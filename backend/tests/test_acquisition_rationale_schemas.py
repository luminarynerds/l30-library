# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tests for AcquisitionRationale Pydantic schemas."""
import pytest
from pydantic import ValidationError

from app.schemas.acquisition_rationale import (
    AcquisitionRationaleCreate,
    AcquisitionRationaleUpdate,
    BehaviorTagRead,
)


def test_create_requires_signal_type():
    with pytest.raises(ValidationError) as exc:
        AcquisitionRationaleCreate(
            primary_use_case_slug='new_parent',
            weeding_condition='current_5yr',
        )
    assert any('signal_type' in str(e['loc']) for e in exc.value.errors())


def test_create_requires_primary_use_case_slug():
    with pytest.raises(ValidationError) as exc:
        AcquisitionRationaleCreate(
            signal_type='other',
            weeding_condition='current_5yr',
        )
    assert any('primary_use_case_slug' in str(e['loc']) for e in exc.value.errors())


def test_create_with_minimum_required():
    schema = AcquisitionRationaleCreate(
        signal_type='gap_in_collection',
        primary_use_case_slug='new_parent',
        weeding_condition='current_5yr',
    )
    # Whether the field surfaces as str or enum depends on config; accept either.
    assert str(schema.signal_type).endswith('gap_in_collection') or schema.signal_type == 'gap_in_collection'
    assert schema.secondary_use_case_slugs == []
    assert schema.anticipated_challenge_reasons == []
    assert schema.anticipated_challenge_acknowledged is False
    assert schema.patron_visible is False


def test_create_rejects_invalid_challenge_reason():
    with pytest.raises(ValidationError):
        AcquisitionRationaleCreate(
            signal_type='other',
            primary_use_case_slug='new_parent',
            weeding_condition='current_5yr',
            anticipated_challenge_reasons=['not_a_real_reason'],
        )


def test_create_accepts_valid_challenge_reasons():
    schema = AcquisitionRationaleCreate(
        signal_type='other',
        primary_use_case_slug='new_parent',
        weeding_condition='current_5yr',
        anticipated_challenge_reasons=['lgbtq_content', 'sexual_content'],
    )
    assert 'lgbtq_content' in schema.anticipated_challenge_reasons


def test_signal_ref_table_without_id_rejected():
    with pytest.raises(ValidationError):
        AcquisitionRationaleCreate(
            signal_type='desk_question',
            primary_use_case_slug='new_parent',
            weeding_condition='current_5yr',
            signal_ref_table='reference_questions',
            # signal_ref_id missing
        )


def test_signal_ref_id_without_table_rejected():
    with pytest.raises(ValidationError):
        AcquisitionRationaleCreate(
            signal_type='desk_question',
            primary_use_case_slug='new_parent',
            weeding_condition='current_5yr',
            signal_ref_id=42,
            # signal_ref_table missing
        )


def test_signal_ref_both_set_ok():
    schema = AcquisitionRationaleCreate(
        signal_type='desk_question',
        primary_use_case_slug='new_parent',
        weeding_condition='current_5yr',
        signal_ref_table='reference_questions',
        signal_ref_id=42,
    )
    assert schema.signal_ref_table == 'reference_questions'
    assert schema.signal_ref_id == 42


def test_signal_ref_both_null_ok():
    schema = AcquisitionRationaleCreate(
        signal_type='other',
        primary_use_case_slug='new_parent',
        weeding_condition='current_5yr',
    )
    assert schema.signal_ref_table is None
    assert schema.signal_ref_id is None


def test_behavior_tag_read_from_attributes():
    """BehaviorTagRead should construct from an object with attributes."""
    class FakeTag:
        slug = 'new_parent'
        label = 'New parent'
        category = 'life_stage'
        description = None
        sort_order = 10
    read = BehaviorTagRead.model_validate(FakeTag())
    assert read.slug == 'new_parent'
    assert read.label == 'New parent'
