# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Property-based tests for notification preference merging.

Targets (pure, app/services/notification_preferences_service.py):
  :52 _merge_preferences  (saved JSON prefs -> full per-type channel list)
  :40 _build_default_pref (via the merge's default branch)

The delivery side (send, retry, dedup) lives in async DB services and is not
property-testable without infrastructure; what IS pure is the contract that
every notification type always surfaces with sane channel defaults no matter
what shape of saved JSON comes back from the user row.
"""
import pytest
from hypothesis import given, strategies as st

from app.services.notification_preferences_service import (
    DEFAULT_NOTIFICATION_TYPES,
    _merge_preferences,
)

pytestmark = pytest.mark.property

KNOWN_TYPES = [ntype for ntype, _, _ in DEFAULT_NOTIFICATION_TYPES]
_META = {ntype: (label, desc) for ntype, label, desc in DEFAULT_NOTIFICATION_TYPES}

channel_dicts = st.dictionaries(
    keys=st.sampled_from(["email", "in_app", "sms", "is_digest"]),
    values=st.booleans(),
)
saved_prefs = st.dictionaries(
    keys=st.one_of(st.sampled_from(KNOWN_TYPES), st.text(max_size=24)),
    values=channel_dicts,
)


@given(saved=saved_prefs)
def test_merge_always_covers_every_type_in_order(saved):
    """Whatever junk is in the saved JSON (unknown keys included), the merge
    returns exactly the canonical type list, in canonical order."""
    merged = _merge_preferences(saved)
    assert [p.notification_type for p in merged] == KNOWN_TYPES


@given(saved=saved_prefs)
def test_merge_characterization(saved):
    """Saved channel flags round-trip; anything unsaved falls back to the
    defaults (email+in_app on, sms+digest off)."""
    for pref in _merge_preferences(saved):
        s = saved.get(pref.notification_type, {})
        assert pref.channel_email is s.get("email", True)
        assert pref.channel_in_app is s.get("in_app", True)
        assert pref.channel_sms is s.get("sms", False)
        assert pref.is_digest is s.get("is_digest", False)


@given(saved=saved_prefs)
def test_labels_and_descriptions_are_canonical(saved):
    """Display strings always come from the canonical table; saved data can
    never overwrite them."""
    for pref in _merge_preferences(saved):
        label, desc = _META[pref.notification_type]
        assert pref.label == label
        assert pref.description == desc
