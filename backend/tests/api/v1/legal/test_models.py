# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tests for legal domain models."""

import pytest
from datetime import datetime
from app.models.legal import (
    LegalGuide,
    LegalForm,
    LegalClinic,
    ComplianceRequirement
)


class TestLegalGuideModel:
    """Test LegalGuide model creation and persistence."""

    def test_legal_guide_model_exists(self):
        """Test that LegalGuide model class exists."""
        assert LegalGuide is not None
        assert hasattr(LegalGuide, '__table__')

    def test_legal_guide_has_required_columns(self):
        """Test that LegalGuide has required columns."""
        table = LegalGuide.__table__
        column_names = [col.name for col in table.columns]
        assert 'id' in column_names
        assert 'title' in column_names
        assert 'slug' in column_names
        assert 'content' in column_names

    def test_legal_guide_slug_is_unique(self):
        """Test that slug column is configured as unique."""
        table = LegalGuide.__table__
        slug_column = table.c.slug
        assert slug_column.unique


class TestLegalFormModel:
    """Test LegalForm model creation and persistence."""

    def test_legal_form_model_exists(self):
        """Test that LegalForm model class exists."""
        assert LegalForm is not None
        assert hasattr(LegalForm, '__table__')

    def test_legal_form_has_required_columns(self):
        """Test that LegalForm has required columns."""
        table = LegalForm.__table__
        column_names = [col.name for col in table.columns]
        assert 'id' in column_names
        assert 'title' in column_names
        assert 'description' in column_names
        assert 'url' in column_names

    def test_legal_form_has_difficulty_level(self):
        """Test that LegalForm has difficulty level column."""
        table = LegalForm.__table__
        column_names = [col.name for col in table.columns]
        assert 'difficulty_level' in column_names


class TestLegalClinicModel:
    """Test LegalClinic model creation and persistence."""

    def test_legal_clinic_model_exists(self):
        """Test that LegalClinic model class exists."""
        assert LegalClinic is not None
        assert hasattr(LegalClinic, '__table__')

    def test_legal_clinic_has_required_columns(self):
        """Test that LegalClinic has required columns."""
        table = LegalClinic.__table__
        column_names = [col.name for col in table.columns]
        assert 'id' in column_names
        assert 'name' in column_names
        assert 'date' in column_names
        assert 'start_time' in column_names
        assert 'end_time' in column_names

    def test_legal_clinic_has_status(self):
        """Test that LegalClinic has status column."""
        table = LegalClinic.__table__
        column_names = [col.name for col in table.columns]
        assert 'status' in column_names


class TestComplianceRequirementModel:
    """Test ComplianceRequirement model creation and persistence."""

    def test_compliance_requirement_model_exists(self):
        """Test that ComplianceRequirement model class exists."""
        assert ComplianceRequirement is not None
        assert hasattr(ComplianceRequirement, '__table__')

    def test_compliance_requirement_has_required_columns(self):
        """Test that ComplianceRequirement has required columns."""
        table = ComplianceRequirement.__table__
        column_names = [col.name for col in table.columns]
        assert 'id' in column_names
        assert 'title' in column_names
        assert 'description' in column_names
        assert 'deadline' in column_names

    def test_compliance_requirement_has_timestamps(self):
        """Test that ComplianceRequirement has timestamp columns."""
        table = ComplianceRequirement.__table__
        column_names = [col.name for col in table.columns]
        assert 'created_at' in column_names
        assert 'updated_at' in column_names
