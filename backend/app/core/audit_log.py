# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

import hashlib
import hmac
import json
import logging
import os
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class AuditLogger:

    # Magic string for the genesis (first) entry
    GENESIS_HASH = "GENESIS"

    def __init__(
        self,
        signing_key: str,
        log_path: str = "/var/log/l30/audit.log",
    ):
        self.signing_key = signing_key.encode() if isinstance(signing_key, str) else signing_key
        self.log_path = log_path
        self._lock = threading.Lock()  # Thread-safe writes
        self._previous_hash = self.GENESIS_HASH

        # Ensure log directory exists
        try:
            log_dir = os.path.dirname(log_path)
            if log_dir and not os.path.exists(log_dir):
                os.makedirs(log_dir, mode=0o700, exist_ok=True)
        except OSError as e:
            logger.error(f"Failed to create audit log directory {log_dir}: {e}")

        # Load existing hash chain on initialization
        self._load_existing_chain()

    def _load_existing_chain(self) -> None:
        if not os.path.exists(self.log_path):
            self._previous_hash = self.GENESIS_HASH
            return

        try:
            with open(self.log_path, "r") as f:
                lines = f.readlines()
                if lines:
                    # Load the last valid entry to get its hash
                    last_entry_str = lines[-1].strip()
                    if last_entry_str:
                        try:
                            last_entry = json.loads(last_entry_str)
                            # The hash chain is: SHA256(entry_json + signature)
                            entry_data = {k: v for k, v in last_entry.items() if k != "signature"}
                            entry_json = json.dumps(entry_data, sort_keys=True)
                            signature = last_entry.get("signature", "")
                            self._previous_hash = hashlib.sha256(
                                (entry_json + signature).encode()
                            ).hexdigest()
                        except (json.JSONDecodeError, KeyError) as e:
                            logger.warning(f"Failed to parse last audit entry: {e}")
                            self._previous_hash = self.GENESIS_HASH
        except (OSError, ValueError) as e:
            logger.error(f"Failed to load existing audit chain: {e}")
            self._previous_hash = self.GENESIS_HASH

    def log(
        self,
        event_type: str,
        user_id: Optional[int] = None,
        email: Optional[str] = None,
        ip_address: Optional[str] = None,
        severity: str = "INFO",
        details: Optional[dict] = None,
    ) -> bool:
        with self._lock:
            try:
                # Build entry without signature first
                entry = {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "event_type": event_type,
                    "severity": severity,
                    "previous_hash": self._previous_hash,
                }

                # Add optional fields
                if user_id is not None:
                    entry["user_id"] = user_id
                if email:
                    entry["email"] = email
                if ip_address:
                    entry["ip_address"] = ip_address
                if details:
                    entry["details"] = details

                # Compute HMAC signature of the entry (before adding signature itself)
                entry_json = json.dumps(entry, sort_keys=True)
                signature = hmac.new(
                    self.signing_key,
                    entry_json.encode(),
                    hashlib.sha256,
                ).hexdigest()

                # Add signature to entry
                entry["signature"] = signature

                # Compute hash chain: hash of (entry_json + signature)
                # This becomes the previous_hash for the next entry
                entry_with_sig_json = json.dumps(entry, sort_keys=True)
                current_hash = hashlib.sha256(entry_with_sig_json.encode()).hexdigest()

                # Write to log file atomically
                signed_line = entry_with_sig_json + "\n"
                with open(self.log_path, "a") as f:
                    f.write(signed_line)
                    f.flush()
                    os.fsync(f.fileno())  # Force write to disk

                # Update in-memory chain
                self._previous_hash = current_hash

                return True

            except Exception as e:
                logger.error(f"Failed to write audit log entry: {e}", exc_info=True)
                return False

    def get_current_chain_hash(self) -> str:
        return self._previous_hash


def verify_audit_log(signing_key: str, log_path: str) -> tuple[bool, list[str]]:
    signing_key_bytes = signing_key.encode() if isinstance(signing_key, str) else signing_key
    errors = []
    previous_hash = AuditLogger.GENESIS_HASH
    entry_count = 0

    if not os.path.exists(log_path):
        return True, ["Log file does not exist (no entries yet)"]

    try:
        with open(log_path, "r") as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue

                entry_count += 1

                # Parse JSON
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError as e:
                    errors.append(f"Line {line_num}: Invalid JSON - {e}")
                    continue

                # Extract signature
                signature = entry.pop("signature", None)
                if not signature:
                    errors.append(f"Line {line_num}: Missing signature")
                    continue

                # Verify HMAC signature
                entry_json = json.dumps(entry, sort_keys=True)
                expected_signature = hmac.new(
                    signing_key_bytes,
                    entry_json.encode(),
                    hashlib.sha256,
                ).hexdigest()

                if signature != expected_signature:
                    errors.append(
                        f"Line {line_num}: HMAC signature mismatch - entry has been tampered with"
                    )
                    continue

                # Verify hash chain
                stored_previous_hash = entry.get("previous_hash")
                if stored_previous_hash != previous_hash:
                    errors.append(
                        f"Line {line_num}: Hash chain broken - expected previous_hash={previous_hash}, got {stored_previous_hash}"
                    )
                    continue

                # Compute current hash for next iteration
                entry["signature"] = signature  # Re-add signature for hash computation
                entry_with_sig = json.dumps(entry, sort_keys=True)
                previous_hash = hashlib.sha256(entry_with_sig.encode()).hexdigest()

    except OSError as e:
        errors.append(f"Error reading log file: {e}")
        return False, errors

    is_valid = len(errors) == 0
    if is_valid:
        errors = [f"✓ Audit log is valid ({entry_count} entries)"]

    return is_valid, errors


# Global audit logger instance (initialized in app startup)
_audit_logger: Optional[AuditLogger] = None
_audit_lock = threading.Lock()


def init_audit_logger(signing_key: str, log_path: str = "/var/log/l30/audit.log") -> None:
    global _audit_logger
    with _audit_lock:
        _audit_logger = AuditLogger(signing_key, log_path)


def get_audit_logger() -> Optional[AuditLogger]:
    return _audit_logger


def audit_log_event(
    event_type: str,
    user_id: Optional[int] = None,
    email: Optional[str] = None,
    ip_address: Optional[str] = None,
    severity: str = "INFO",
    details: Optional[dict] = None,
) -> bool:
    audit_logger = get_audit_logger()
    if not audit_logger:
        logger.warning("Audit logger not initialized")
        return False

    return audit_logger.log(
        event_type=event_type,
        user_id=user_id,
        email=email,
        ip_address=ip_address,
        severity=severity,
        details=details,
    )
