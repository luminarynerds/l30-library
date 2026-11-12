# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

import hashlib
import ipaddress
import json
from app.core.logging import get_logger
import secrets
import string
import base64

import pyotp
from cryptography.fernet import Fernet, InvalidToken
import bcrypt

from .config import get_settings
from .branding import branding

logger = get_logger(__name__)
settings = get_settings()

# Recovery code hashing (bcrypt, same as passwords)

# TOTP configuration
TOTP_ISSUER = branding.library_name
TOTP_DIGITS = 6
TOTP_INTERVAL = 30  # seconds
TOTP_VALID_WINDOW = 1  # Allow 1 period before/after (handles clock drift)
RECOVERY_CODE_COUNT = 8
RECOVERY_CODE_LENGTH = 8  # 8 alphanumeric characters per code
MAX_2FA_ATTEMPTS = 5  # Max attempts per pending token


def generate_totp_secret() -> str:
    return pyotp.random_base32(length=32)


def _derive_fernet(secret_material: str) -> Fernet:
    key_material = f"totp-encryption-{secret_material}".encode()
    key = hashlib.sha256(key_material).digest()
    fernet_key = base64.urlsafe_b64encode(key)
    return Fernet(fernet_key)


def _get_totp_fernet() -> Fernet:
    """Current TOTP encryption key. Keyed on TOTP_ENCRYPTION_KEY (dedicated
    secret, so a SECRET_KEY compromise doesn't also let an attacker mint valid
    2FA codes -- mirrors TOKEN_ENCRYPTION_KEY's split from encryption.py).
    Falls back to the legacy SECRET_KEY-derived key when unset, so existing
    deployments that haven't set the new var see no behavior change."""
    return _derive_fernet(settings.totp_encryption_key or settings.secret_key)


def _get_totp_fernet_previous() -> Fernet | None:
    """Rotated-out TOTP_ENCRYPTION_KEY_PREVIOUS, for TOTP_ENCRYPTION_KEY
    rotation (mirrors PII_ENCRYPTION_KEY_PREVIOUS)."""
    if not settings.totp_encryption_key_previous:
        return None
    return _derive_fernet(settings.totp_encryption_key_previous)


def _get_totp_fernet_legacy() -> Fernet | None:
    """The pre-key-separation derivation (always SECRET_KEY-based). Only
    relevant once TOTP_ENCRYPTION_KEY is set (and therefore differs from the
    legacy derivation) -- lets already-enrolled users' secrets, encrypted
    before the key split shipped, keep decrypting during migration.
    Equivalent to _get_totp_fernet() when TOTP_ENCRYPTION_KEY is unset, so
    it's skipped then to avoid a pointless duplicate attempt."""
    if not settings.totp_encryption_key:
        return None
    return _derive_fernet(settings.secret_key)


def encrypt_totp_secret(secret: str) -> str:
    f = _get_totp_fernet()
    return f.encrypt(secret.encode()).decode()


def _decrypt_totp_secret_ex(encrypted: str) -> tuple[str, bool]:
    """Decrypt trying the current key, then the previous (rotated-out) key,
    then the legacy SECRET_KEY-derived key. Returns (plaintext, was_current).
    Raises ValueError once none of them can decrypt it, or immediately if
    `encrypted` isn't even a decryptable-shaped string (e.g. None from a
    data-integrity edge where totp_enabled=True but totp_secret is unset) --
    callers rely on ValueError being the single failure mode this raises, so
    a malformed/missing input must not surface as a bare AttributeError/
    TypeError instead."""
    if not isinstance(encrypted, str) or not encrypted:
        raise ValueError("Failed to decrypt TOTP secret")
    candidates = (
        (_get_totp_fernet(), True),
        (_get_totp_fernet_previous(), False),
        (_get_totp_fernet_legacy(), False),
    )
    for fernet, is_current in candidates:
        if fernet is None:
            continue
        try:
            return fernet.decrypt(encrypted.encode()).decode(), is_current
        except (InvalidToken, ValueError):
            continue
    # No legacy XOR-encrypted secrets exist (2FA has never been enabled for
    # any account without going through one of the keys above), so exhausting
    # every key is a hard error, not a fallback to a home-rolled XOR cipher.
    raise ValueError("Failed to decrypt TOTP secret")


def decrypt_totp_secret(encrypted: str) -> str:
    plaintext, _was_current = _decrypt_totp_secret_ex(encrypted)
    return plaintext


def decrypt_totp_secret_and_migrate(encrypted: str) -> tuple[str, str | None]:
    """Like decrypt_totp_secret, but also returns fresh ciphertext to persist
    when the secret was decrypted via the previous or legacy key (lazy
    read-old-write-new migration to the current TOTP_ENCRYPTION_KEY). The
    second element is None when the secret was already on the current key.
    Raises ValueError if it can't be decrypted at all."""
    plaintext, was_current = _decrypt_totp_secret_ex(encrypted)
    if was_current:
        return plaintext, None
    return plaintext, encrypt_totp_secret(plaintext)


def get_totp_uri(secret: str, email: str) -> str:
    totp = pyotp.TOTP(secret, digits=TOTP_DIGITS, interval=TOTP_INTERVAL)
    return totp.provisioning_uri(name=email, issuer_name=TOTP_ISSUER)


def verify_totp_code(secret: str, code: str) -> bool:
    if not code or not code.isdigit() or len(code) != TOTP_DIGITS:
        return False
    totp = pyotp.TOTP(secret, digits=TOTP_DIGITS, interval=TOTP_INTERVAL)
    return totp.verify(code, valid_window=TOTP_VALID_WINDOW)


async def verify_totp_code_once(secret: str, code: str, user_id: int) -> bool:
    if not verify_totp_code(secret, code):
        return False
    # Check replay via Redis
    try:
        import redis.asyncio as aioredis
        r = aioredis.from_url(settings.redis_url)
        replay_key = f"totp_used:{user_id}:{code}"
        was_set = await r.set(replay_key, "1", nx=True, ex=90)  # 90s = TOTP_INTERVAL * 3
        await r.aclose()
        if not was_set:
            return False  # Code already used
        return True
    except Exception:  # noqa: BLE001  # fail-open boundary — Redis outage must not block 2FA verification
        # If Redis is down, allow the code (fail-open for availability)
        return True


def generate_recovery_codes() -> tuple[list[str], list[str]]:
    # Remove ambiguous characters (0/O, 1/I/L)
    alphabet = string.ascii_uppercase + string.digits
    for ch in "0O1IL":
        alphabet = alphabet.replace(ch, "")

    plain_codes = []
    hashed_codes = []

    for _ in range(RECOVERY_CODE_COUNT):
        code = "".join(secrets.choice(alphabet) for _ in range(RECOVERY_CODE_LENGTH))
        # Format as XXXX-XXXX for readability
        formatted = f"{code[:4]}-{code[4:]}"
        plain_codes.append(formatted)
        hashed_codes.append(bcrypt.hashpw(code.encode("utf-8"), bcrypt.gensalt()).decode("utf-8"))  # Hash without dashes

    return plain_codes, hashed_codes


def verify_recovery_code(code: str, hashed_codes: list[str]) -> int | None:
    # Strip dashes and whitespace, uppercase
    clean_code = code.replace("-", "").replace(" ", "").upper()

    for i, hashed in enumerate(hashed_codes):
        if hashed and bcrypt.checkpw(clean_code.encode("utf-8"), hashed.encode("utf-8")):
            return i
    return None


def compute_device_hash(user_agent: str, ip_address: str) -> str:
    try:
        ip = ipaddress.ip_address(ip_address)
        if isinstance(ip, ipaddress.IPv4Address):
            network = ipaddress.ip_network(f"{ip_address}/24", strict=False)
            subnet = str(network.network_address)
        else:
            # IPv6: use /48 prefix
            network = ipaddress.ip_network(f"{ip_address}/48", strict=False)
            subnet = str(network.network_address)
    except ValueError:
        subnet = ip_address  # Fallback to raw IP

    raw = f"{user_agent}|{subnet}"
    return hashlib.sha256(raw.encode()).hexdigest()


def parse_user_agent(ua_string: str) -> str:
    if not ua_string:
        return "Unknown Device"

    ua = ua_string.lower()

    # Detect browser
    browser = "Unknown Browser"
    if "edg/" in ua or "edge/" in ua:
        browser = "Edge"
    elif "opr/" in ua or "opera" in ua:
        browser = "Opera"
    elif "chrome/" in ua and "chromium" not in ua:
        browser = "Chrome"
    elif "firefox/" in ua:
        browser = "Firefox"
    elif "safari/" in ua and "chrome" not in ua:
        browser = "Safari"
    elif "msie" in ua or "trident" in ua:
        browser = "Internet Explorer"

    # Detect OS/device
    device = "Unknown OS"
    if "iphone" in ua:
        device = "iPhone"
    elif "ipad" in ua:
        device = "iPad"
    elif "android" in ua:
        device = "Android"
    elif "macintosh" in ua or "mac os x" in ua:
        device = "Mac"
    elif "windows" in ua:
        device = "Windows"
    elif "linux" in ua:
        device = "Linux"
    elif "chromeos" in ua or "cros" in ua:
        device = "ChromeOS"

    return f"{browser} on {device}"
