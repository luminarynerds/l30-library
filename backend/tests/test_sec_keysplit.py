# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Regression tests for the key-separation batch (findings #8, #10).

#8  TOTP secrets: the home-rolled XOR fallback is gone. Decryption either
    succeeds via Fernet or raises; it never silently reinterprets ciphertext
    with a repeating-key XOR "cipher".
#10 Blind-index and token keys must be derivable from dedicated secrets, not
    silently collapsed onto SECRET_KEY:
      a) hash_pii keys on PII_HASH_KEY when set;
      b) token encryption keys on TOKEN_ENCRYPTION_KEY when set;
      c) production refuses to boot with PII encryption on but PII_HASH_KEY unset.
"""

import os
import pathlib
import shutil
import subprocess
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from cryptography.fernet import Fernet

BACKEND = pathlib.Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND.parent


def _src(rel: str) -> str:
    return (BACKEND / rel).read_text()


def run_setup_sh(tmp_path: pathlib.Path) -> dict:
    """Copy setup.sh + its inputs into tmp_path, run it non-interactively via
    the --domain/--email/--name flags, and parse the resulting .env into a
    dict."""
    for name in ("setup.sh", ".env.dist", "branding.json.example"):
        shutil.copy(REPO_ROOT / name, tmp_path / name)
    (tmp_path / "setup.sh").chmod(0o755)

    result = subprocess.run(
        [
            "bash",
            "setup.sh",
            "--domain",
            "library.example.org",
            "--email",
            "hello@library.example.org",
            "--name",
            "Test Library",
        ],
        cwd=tmp_path,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, f"setup.sh failed:\n{result.stdout}\n{result.stderr}"

    env = {}
    for line in (tmp_path / ".env").read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        env[key] = value
    return env


# ---- #8 TOTP XOR fallback removed ----


def test_totp_source_has_no_xor_fallback():
    # The actual fallback code (repeating-key XOR over base64-decoded bytes) is
    # gone; only the Fernet path and a hard raise remain.
    s = _src("app/core/totp.py")
    assert "e ^ key[i % len(key)]" not in s
    assert "from base64 import b64decode" not in s
    assert "b64decode(encrypted" not in s


def test_totp_roundtrip_and_hard_failure():
    try:
        from app.core.totp import decrypt_totp_secret, encrypt_totp_secret
    except Exception as e:  # noqa: BLE001  # degraded host venv can't construct BrandingSettings
        pytest.skip(f"totp import unavailable in this env: {e}")
    secret = "JBSWY3DPEHPK3PXP"
    assert decrypt_totp_secret(encrypt_totp_secret(secret)) == secret
    with pytest.raises(ValueError, match="Failed to decrypt TOTP secret"):
        decrypt_totp_secret("not-a-valid-fernet-token")


# ---- #10a hash_pii keys on the dedicated PII_HASH_KEY ----


def test_hash_pii_uses_dedicated_key_when_set():
    from app.core import encryption

    dedicated = SimpleNamespace(pii_hash_key="dedicated", secret_key="sessionsecret")
    fallback = SimpleNamespace(pii_hash_key="", secret_key="sessionsecret")
    with patch("app.core.config.get_settings", return_value=dedicated):
        h_dedicated = encryption.hash_pii("7405550101", field="phone")
    with patch("app.core.config.get_settings", return_value=fallback):
        h_fallback = encryption.hash_pii("7405550101", field="phone")
    # Distinct keys must produce distinct blind indexes (no silent collapse).
    assert h_dedicated != h_fallback


# ---- #10b token encryption keys on the dedicated TOKEN_ENCRYPTION_KEY ----


def test_token_fernet_uses_dedicated_key_when_set():
    from app.core import encryption

    dedicated = SimpleNamespace(token_encryption_key="tokenkey", secret_key="sessionsecret")
    fallback = SimpleNamespace(token_encryption_key="", secret_key="sessionsecret")
    with patch("app.core.config.get_settings", return_value=dedicated):
        ct = encryption.encrypt_token("vendor-api-key")
        assert encryption.decrypt_token(ct) == "vendor-api-key"
    # A token sealed under the dedicated key is NOT readable under the fallback
    # key: the two secrets are genuinely separated.
    with patch("app.core.config.get_settings", return_value=fallback):
        assert encryption.decrypt_token(ct) == ct  # InvalidToken -> passthrough


# ---- #10c production boot guard ----


def test_production_requires_pii_hash_key():
    base = {
        "ENVIRONMENT": "production",
        "SECRET_KEY": "x" * 40,
        "DATABASE_URL": "postgresql+asyncpg://u:p@h/db",
        "PII_ENCRYPTION_ENABLED": "true",
        "PII_ENCRYPTION_KEY": Fernet.generate_key().decode(),
        "WATERMARK_SECRET_SALT": "realsalt",
        "DOWNLOAD_IP_HASH_SALT": "realsalt2",
    }
    from app.core.config import Settings

    with patch.dict(os.environ, {**base, "PII_HASH_KEY": ""}, clear=True):
        with pytest.raises(ValueError, match="PII_HASH_KEY must be set"):
            Settings()
    with patch.dict(os.environ, {**base, "PII_HASH_KEY": "dedicated-hash-key"}, clear=True):
        assert Settings().pii_hash_key == "dedicated-hash-key"


def test_production_requires_pii_encryption_enabled():
    """Production must not boot with PII encryption switched off: every
    EncryptedString/EncryptedText column would silently store plaintext
    (encrypt_pii returns its input when the feature is disabled), and every
    check that reads model source or column widths would still look green."""
    base = {
        "ENVIRONMENT": "production",
        "SECRET_KEY": "x" * 40,
        "DATABASE_URL": "postgresql+asyncpg://u:p@h/db",
        "PII_ENCRYPTION_KEY": Fernet.generate_key().decode(),
        "PII_HASH_KEY": "dedicated-hash-key",
        "WATERMARK_SECRET_SALT": "realsalt",
        "DOWNLOAD_IP_HASH_SALT": "realsalt2",
    }
    from app.core.config import Settings

    with patch.dict(os.environ, {**base, "PII_ENCRYPTION_ENABLED": "false"}, clear=True):
        with pytest.raises(ValueError, match="PII_ENCRYPTION_ENABLED must be true"):
            Settings()
    # Same env outside production still boots: local dev without a key setup.
    with patch.dict(
        os.environ,
        {**base, "ENVIRONMENT": "development", "PII_ENCRYPTION_ENABLED": "false"},
        clear=True,
    ):
        assert Settings().pii_encryption_enabled is False


# ---- production must refuse the published CHANGE_ME placeholder as a signing key ----

# PII encryption on (production refuses to boot without it); these tests are
# about the placeholder signing keys, not the encryption gate.
_PROD_BASE = {
    "ENVIRONMENT": "production",
    "DATABASE_URL": "postgresql+asyncpg://u:p@h/db",
    "PII_ENCRYPTION_ENABLED": "true",
    "PII_ENCRYPTION_KEY": Fernet.generate_key().decode(),
    "PII_HASH_KEY": "dedicated-hash-key",
    "WATERMARK_SECRET_SALT": "realsalt",
    "DOWNLOAD_IP_HASH_SALT": "realsalt2",
}


def test_production_rejects_placeholder_secret_key():
    """The .env.dist placeholder is public; booting production with it would let
    anyone forge admin JWTs (signing_key falls back to SECRET_KEY)."""
    from app.core.config import Settings

    with patch.dict(os.environ, {**_PROD_BASE, "SECRET_KEY": "CHANGE_ME"}, clear=True):
        with pytest.raises(ValueError, match="SECRET_KEY"):
            Settings()
    # A real secret boots fine.
    with patch.dict(os.environ, {**_PROD_BASE, "SECRET_KEY": "s" * 48}, clear=True):
        assert Settings().secret_key == "s" * 48


def test_production_rejects_placeholder_jwt_secret_key():
    """If a dedicated JWT signing key is set, it also must not be the placeholder;
    empty is fine (signing falls back to the now-guarded SECRET_KEY)."""
    from app.core.config import Settings

    base = {**_PROD_BASE, "SECRET_KEY": "s" * 48}
    with patch.dict(os.environ, {**base, "JWT_SECRET_KEY": "CHANGE_ME"}, clear=True):
        with pytest.raises(ValueError, match="JWT_SECRET_KEY"):
            Settings()
    with patch.dict(os.environ, {**base, "JWT_SECRET_KEY": ""}, clear=True):
        assert Settings().jwt_secret_key == ""


# ---- C3: TOKEN_ENCRYPTION_KEY unset in production warns, does not hard-fail ----


def test_production_warns_but_does_not_fail_when_token_encryption_key_unset(caplog):
    """Existing fork-and-gift installs never set TOKEN_ENCRYPTION_KEY. Unlike
    PII_HASH_KEY, this must WARN loudly, not raise -- hard-failing would break
    their next rebuild (maintainer call, 2026-07 Fernet audit finding C3)."""
    base = {
        "ENVIRONMENT": "production",
        "SECRET_KEY": "x" * 40,
        "DATABASE_URL": "postgresql+asyncpg://u:p@h/db",
        "PII_ENCRYPTION_ENABLED": "true",
        "PII_ENCRYPTION_KEY": Fernet.generate_key().decode(),
        "PII_HASH_KEY": "dedicated-hash-key",
        "WATERMARK_SECRET_SALT": "realsalt",
        "DOWNLOAD_IP_HASH_SALT": "realsalt2",
    }
    from app.core.config import Settings

    with patch.dict(os.environ, {**base, "TOKEN_ENCRYPTION_KEY": ""}, clear=True):
        with caplog.at_level("WARNING"):
            settings = Settings()
    assert settings.token_encryption_key == ""
    assert any("TOKEN_ENCRYPTION_KEY" in rec.message for rec in caplog.records)

    with patch.dict(
        os.environ, {**base, "TOKEN_ENCRYPTION_KEY": "dedicated-token-key"}, clear=True
    ):
        assert Settings().token_encryption_key == "dedicated-token-key"


# ---- setup.sh must actually generate the PII_HASH_KEY it requires (fresh-install defect) ----


def test_setup_sh_generates_pii_hash_key(tmp_path):
    env = run_setup_sh(tmp_path)
    assert "PII_HASH_KEY" in env
    assert len(env["PII_HASH_KEY"]) == 64


# ---- non-interactive flag parsing (fork-and-deploy pipeline defect) ----


def _stage_setup_sh(tmp_path: pathlib.Path) -> None:
    for name in ("setup.sh", ".env.dist", "branding.json.example"):
        shutil.copy(REPO_ROOT / name, tmp_path / name)
    (tmp_path / "setup.sh").chmod(0o755)


def test_setup_sh_accepts_noninteractive_flags(tmp_path):
    """A scripted fork-and-deploy pipeline has no TTY and can't answer `read`
    prompts. --domain/--email/--name must fully drive the install with no
    stdin at all."""
    _stage_setup_sh(tmp_path)
    result = subprocess.run(
        [
            "bash",
            "setup.sh",
            "--domain",
            "yourlibrary.example",
            "--email",
            "admin@yourlibrary.example",
            "--name",
            "Test Library",
        ],
        cwd=tmp_path,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, f"setup.sh failed:\n{result.stdout}\n{result.stderr}"

    env = {}
    for line in (tmp_path / ".env").read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        env[key] = value

    assert env["DOMAIN"] == "yourlibrary.example"
    assert env["FROM_EMAIL"] == "admin@yourlibrary.example"
    assert env["LIBRARY_NAME"] == "Test Library"
    assert "PII_HASH_KEY" in env
    assert len(env["PII_HASH_KEY"]) == 64
    import re

    assert re.fullmatch(r"[0-9a-f]{64}", env["PII_HASH_KEY"])


def test_setup_sh_missing_flag_non_tty_errors_clearly(tmp_path):
    """No TTY and a missing required flag must fail fast with a clear error,
    never hang waiting on a `read` that can never be answered."""
    _stage_setup_sh(tmp_path)
    result = subprocess.run(
        ["bash", "setup.sh", "--domain", "yourlibrary.example", "--name", "Test Library"],
        cwd=tmp_path,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode != 0
    combined = result.stdout + result.stderr
    assert "email" in combined.lower()
    assert not (tmp_path / ".env").exists()
