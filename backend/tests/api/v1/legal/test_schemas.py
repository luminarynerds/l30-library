# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tests for legal domain schemas."""

import pytest
from app.schemas.legal import (
    LegalGuideBase,
    LegalGuideCreate,
    LegalGuideUpdate,
    LegalGuideResponse,
    LegalFormBase,
    LegalFormCreate,
    LegalFormResponse,
    LegalClinicBase,
    LegalClinicCreate,
    LegalClinicResponse,
    ComplianceRequirementBase,
    ComplianceRequirementCreate,
    ComplianceRequirementResponse,
)


class TestLegalGuideSchemas:
    """Test LegalGuide schema classes exist and are importable."""

    def test_legal_guide_base_exists(self):
        """Test that LegalGuideBase schema exists."""
        assert LegalGuideBase is not None

    def test_legal_guide_create_exists(self):
        """Test that LegalGuideCreate schema exists."""
        assert LegalGuideCreate is not None

    def test_legal_guide_update_exists(self):
        """Test that LegalGuideUpdate schema exists."""
        assert LegalGuideUpdate is not None

    def test_legal_guide_response_exists(self):
        """Test that LegalGuideResponse schema exists."""
        assert LegalGuideResponse is not None


class TestLegalFormSchemas:
    """Test LegalForm schema classes exist and are importable."""

    def test_legal_form_base_exists(self):
        """Test that LegalFormBase schema exists."""
        assert LegalFormBase is not None

    def test_legal_form_create_exists(self):
        """Test that LegalFormCreate schema exists."""
        assert LegalFormCreate is not None

    def test_legal_form_response_exists(self):
        """Test that LegalFormResponse schema exists."""
        assert LegalFormResponse is not None


class TestLegalClinicSchemas:
    """Test LegalClinic schema classes exist and are importable."""

    def test_legal_clinic_base_exists(self):
        """Test that LegalClinicBase schema exists."""
        assert LegalClinicBase is not None

    def test_legal_clinic_create_exists(self):
        """Test that LegalClinicCreate schema exists."""
        assert LegalClinicCreate is not None

    def test_legal_clinic_response_exists(self):
        """Test that LegalClinicResponse schema exists."""
        assert LegalClinicResponse is not None


class TestComplianceRequirementSchemas:
    """Test ComplianceRequirement schema classes exist and are importable."""

    def test_compliance_requirement_base_exists(self):
        """Test that ComplianceRequirementBase schema exists."""
        assert ComplianceRequirementBase is not None

    def test_compliance_requirement_create_exists(self):
        """Test that ComplianceRequirementCreate schema exists."""
        assert ComplianceRequirementCreate is not None

    def test_compliance_requirement_response_exists(self):
        """Test that ComplianceRequirementResponse schema exists."""
        assert ComplianceRequirementResponse is not None
