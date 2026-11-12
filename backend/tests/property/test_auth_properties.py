# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Property-based tests for auth primitives.

Targets (pure, app/core/security.py):
  :283 create_access_token / :388 verify_token  (JWT claim round-trip)
  :231 validate_password                        (strength rules)
  :265 hash_password / :255 verify_password     (bcrypt round-trip)
  :341 hash_reset_token / :348 verify_reset_token

verify_token is called with check_revocation=False throughout: revocation
checking is the one impure path in this module (Redis at :147), and this
suite is pure-function only.
"""
from datetime import timedelta

import jwt
import pytest
from hypothesis import given, settings as hyp_settings, strategies as st
from jwt.exceptions import PyJWTError

from app.core.config import get_settings
from app.core.security import (
    COMMON_PASSWORDS,
    PasswordValidationError,
    create_access_token,
    hash_password,
    hash_reset_token,
    validate_password,
    verify_password,
    verify_reset_token,
    verify_token,
)

pytestmark = pytest.mark.property

_settings = get_settings()

subjects = st.text(
    alphabet=st.characters(min_codepoint=33, max_codepoint=126),
    min_size=1,
    max_size=32,
)
emails = st.from_regex(r"[a-z]{1,10}@[a-z]{1,10}\.(org|com|net)", fullmatch=True)
roles = st.sampled_from(["patron", "staff", "admin", "teacher"])


@given(sub=subjects, email=emails, role=roles, branch_id=st.integers(1, 10_000))
def test_token_claims_round_trip(sub, email, role, branch_id):
    """Every claim that goes into a token must come back out unchanged."""
    token = create_access_token(sub, email=email, role=role, branch_id=branch_id)
    payload = verify_token(token, check_revocation=False)
    assert payload["sub"] == sub
    assert payload["email"] == email
    assert payload["role"] == role
    assert payload["branch_id"] == branch_id
    assert payload["type"] == "access"


@given(sub=subjects)
def test_token_synthesizes_default_email(sub):
    """verify_token rejects tokens without an email claim, so token creation
    must always backfill one."""
    payload = verify_token(create_access_token(sub), check_revocation=False)
    assert payload["email"] == f"user-{sub}@library.local"


@given(sub=subjects, seconds_past=st.integers(min_value=5, max_value=10**6))
def test_expired_token_always_rejected(sub, seconds_past):
    token = create_access_token(sub, expires_delta=timedelta(seconds=-seconds_past))
    with pytest.raises(jwt.ExpiredSignatureError):
        verify_token(token, check_revocation=False)


@given(sub=subjects, data=st.data())
def test_tampered_token_always_rejected(sub, data):
    """Flipping any signature character that carries signature bits must
    invalidate the token against every configured key.

    The final character is excluded: a 256-bit HMAC base64url-encodes to 43
    chars (258 bits), so the last char's low 2 bits are padding that PyJWT's
    decoder ignores (RFC 7515 base64 malleability) -- flipping only padding
    bits yields a byte-identical signature, which Hypothesis duly found."""
    token = create_access_token(sub)
    header, payload, sig = token.split(".")
    pos = data.draw(st.integers(min_value=0, max_value=len(sig) - 2))
    replacement = data.draw(
        st.sampled_from("abcdefghijklmnopqrstuvwxyzABCDEFGHIJ0123456789").filter(
            lambda c: c != sig[pos]
        )
    )
    tampered = f"{header}.{payload}.{sig[:pos]}{replacement}{sig[pos + 1:]}"
    with pytest.raises(PyJWTError):
        verify_token(tampered, check_revocation=False)


# bcrypt is intentionally slow (~250ms/hash), so keep example counts small.
@hyp_settings(max_examples=5)
@given(
    password=st.text(
        alphabet=st.characters(min_codepoint=33, max_codepoint=126),
        min_size=8,
        max_size=40,
    )
)
def test_password_hash_round_trip_and_salted(password):
    h1 = hash_password(password)
    h2 = hash_password(password)
    assert h1 != password, "Password stored in the clear"
    assert h1 != h2, "Identical hashes imply a static salt"
    assert verify_password(password, h1)
    assert verify_password(password, h2)


@hyp_settings(max_examples=5)
@given(
    password=st.text(
        alphabet=st.characters(min_codepoint=33, max_codepoint=126),
        min_size=8,
        max_size=40,
    ),
    other=st.text(
        alphabet=st.characters(min_codepoint=33, max_codepoint=126),
        min_size=8,
        max_size=40,
    ),
)
def test_wrong_password_never_verifies(password, other):
    if password == other:
        return
    assert not verify_password(other, hash_password(password))


@given(
    password=st.text(
        alphabet=st.characters(
            min_codepoint=33, max_codepoint=126, exclude_characters="0123456789"
        ),
        max_size=60,
    )
)
def test_digitless_password_always_rejected(password):
    with pytest.raises(PasswordValidationError):
        validate_password(password)


@given(size=st.integers(min_value=0, max_value=max(_settings.password_min_length - 1, 0)))
def test_short_password_always_rejected(size):
    # "Aa1!" repeated guarantees every class rule is met below min length,
    # isolating the length rule.
    password = ("Aa1!" * (size // 4 + 1))[:size]
    with pytest.raises(PasswordValidationError):
        validate_password(password)


@given(
    body=st.text(alphabet="abcdefghijklmnopqrstuvwxyz", min_size=8, max_size=24)
)
def test_compliant_password_accepted(body):
    password = f"Xq7${body}"
    if password.lower() in COMMON_PASSWORDS:
        return
    validate_password(password)  # must not raise


@given(token=st.text(min_size=1, max_size=64))
def test_reset_token_round_trip(token):
    assert verify_reset_token(token, hash_reset_token(token))


@given(t1=st.text(min_size=1, max_size=64), t2=st.text(min_size=1, max_size=64))
def test_reset_token_mismatch_rejected(t1, t2):
    if t1 == t2:
        return
    assert not verify_reset_token(t2, hash_reset_token(t1))
