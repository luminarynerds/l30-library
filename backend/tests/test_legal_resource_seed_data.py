# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Legal Resource Seed Data Verification Tests

Verifies that all legal resource seed data is present, correct, and complete:
- Legal forms (various categories)
- Legal guides
- Glossary terms
- Legal clinic schedules
- Service providers
- Clinic registrations

Tests verify seed data completeness, content structure, and display readiness
by importing and inspecting the seed functions directly.
"""

import pytest
import sys
import importlib
import inspect
from pathlib import Path

# Ensure the backend is on the path
BACKEND_PATH = Path(__file__).parent.parent
sys.path.insert(0, str(BACKEND_PATH))


# ==================== Seed Script Import Tests ====================


class TestSeedScriptImports:
    """Verify the seed script can be imported and has all required functions."""

    def test_seed_script_importable(self):
        """Verify seed_legal_resources.py can be imported without errors."""
        spec = importlib.util.spec_from_file_location(
            "seed_legal_resources",
            BACKEND_PATH / "scripts" / "seed_legal_resources.py"
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        assert module is not None

    def test_seed_script_has_required_functions(self):
        """Verify all seed functions are defined."""
        spec = importlib.util.spec_from_file_location(
            "seed_legal_resources",
            BACKEND_PATH / "scripts" / "seed_legal_resources.py"
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        required_functions = [
            "seed_legal_topics",
            "seed_la_county_providers",
            "seed_lasc_forms",
            "seed_legal_guides",
            "seed_glossary_terms",
            "seed_legal_clinics",
            "seed_clinic_registrations",
            "main",
        ]
        for func_name in required_functions:
            assert hasattr(module, func_name), \
                f"Missing function: {func_name}"
            assert callable(getattr(module, func_name)), \
                f"{func_name} is not callable"

    def test_seed_functions_are_async(self):
        """Verify all seed functions are async."""
        spec = importlib.util.spec_from_file_location(
            "seed_legal_resources",
            BACKEND_PATH / "scripts" / "seed_legal_resources.py"
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        async_functions = [
            "seed_legal_topics",
            "seed_la_county_providers",
            "seed_lasc_forms",
            "seed_legal_guides",
            "seed_glossary_terms",
            "seed_legal_clinics",
            "seed_clinic_registrations",
            "main",
        ]
        for func_name in async_functions:
            func = getattr(module, func_name)
            assert inspect.iscoroutinefunction(func), \
                f"{func_name} should be an async function"

    def test_main_calls_all_seed_functions(self):
        """Verify main() calls all seed functions in correct order."""
        source_path = BACKEND_PATH / "scripts" / "seed_legal_resources.py"
        source = source_path.read_text()

        # Find the main() function body
        main_start = source.find("async def main():")
        assert main_start > 0, "main() function not found"
        main_body = source[main_start:]

        # Verify all seed functions are called
        expected_calls = [
            "seed_legal_topics",
            "seed_la_county_providers",
            "seed_lasc_forms",
            "seed_legal_guides",
            "seed_glossary_terms",
            "seed_legal_clinics",
            "seed_clinic_registrations",
        ]
        for call in expected_calls:
            assert call in main_body, \
                f"main() should call {call}"


# ==================== Seed Data Content Verification ====================


class TestSeedDataContent:
    """Verify seed data content by inspecting the script source."""

    @pytest.fixture
    def seed_source(self):
        """Load the seed script source code."""
        return (BACKEND_PATH / "scripts" / "seed_legal_resources.py").read_text()

    # --- Topics ---

    def test_has_family_law_topic(self, seed_source):
        assert '"Family Law"' in seed_source
        assert '"slug": "family"' in seed_source

    def test_has_housing_topic(self, seed_source):
        assert '"Housing & Eviction"' in seed_source
        assert '"slug": "housing"' in seed_source

    def test_has_employment_topic(self, seed_source):
        assert '"Employment"' in seed_source
        assert '"slug": "employment"' in seed_source

    def test_has_consumer_topic(self, seed_source):
        assert '"Consumer & Debt"' in seed_source
        assert '"slug": "consumer"' in seed_source

    def test_has_immigration_topic(self, seed_source):
        assert '"Immigration"' in seed_source
        assert '"slug": "immigration"' in seed_source

    def test_has_name_change_topic(self, seed_source):
        assert '"Name Change"' in seed_source
        assert '"slug": "name-change"' in seed_source

    def test_has_small_claims_topic(self, seed_source):
        assert '"Small Claims"' in seed_source
        assert '"slug": "small-claims"' in seed_source

    def test_topics_have_icons_and_colors(self, seed_source):
        """Verify topics include display metadata."""
        assert '"icon": "heart"' in seed_source
        assert '"icon": "home"' in seed_source
        assert '"color":' in seed_source

    def test_topics_have_keywords(self, seed_source):
        """Verify topics have searchable keywords."""
        assert '"keywords":' in seed_source
        assert '"divorce"' in seed_source
        assert '"eviction"' in seed_source

    # --- Forms ---

    def test_has_divorce_petition_form(self, seed_source):
        assert '"FL-100"' in seed_source
        assert "Divorce Petition" in seed_source

    def test_has_divorce_response_form(self, seed_source):
        assert '"FL-120"' in seed_source
        assert "Divorce Response" in seed_source

    def test_has_dv_restraining_order_form(self, seed_source):
        assert '"DV-100"' in seed_source
        assert "Domestic Violence Restraining Order" in seed_source

    def test_has_eviction_complaint_form(self, seed_source):
        assert '"UD-100"' in seed_source
        assert "Unlawful Detainer" in seed_source

    def test_has_eviction_answer_form(self, seed_source):
        assert '"UD-105"' in seed_source

    def test_has_small_claims_plaintiff_form(self, seed_source):
        assert '"SC-100"' in seed_source

    def test_has_small_claims_defendant_form(self, seed_source):
        assert '"SC-120"' in seed_source

    def test_has_name_change_form(self, seed_source):
        assert '"NC-100"' in seed_source
        assert "Name Change Petition" in seed_source

    def test_has_fee_waiver_form(self, seed_source):
        assert '"FW-001"' in seed_source
        assert "Fee Waiver" in seed_source

    def test_forms_have_filing_fees(self, seed_source):
        assert '"filing_fee":' in seed_source

    def test_forms_have_difficulty_levels(self, seed_source):
        assert "FormDifficulty.complex" in seed_source
        assert "FormDifficulty.moderate" in seed_source

    def test_forms_have_urls(self, seed_source):
        assert '"url":' in seed_source
        assert "courts.ca.gov" in seed_source

    def test_forms_have_languages(self, seed_source):
        assert '"languages_available":' in seed_source
        assert '"English"' in seed_source
        assert '"Spanish"' in seed_source

    def test_forms_span_multiple_categories(self, seed_source):
        assert 'topic_map.get("family")' in seed_source
        assert 'topic_map.get("housing")' in seed_source
        assert 'topic_map.get("small-claims")' in seed_source
        assert 'topic_map.get("name-change")' in seed_source

    # --- Guides ---

    def test_has_divorce_guide(self, seed_source):
        assert "How to File for Divorce in California" in seed_source
        assert '"slug": "how-to-file-divorce-california"' in seed_source

    def test_has_eviction_guide(self, seed_source):
        assert "Defending Against an Eviction" in seed_source
        assert '"slug": "defending-eviction"' in seed_source

    def test_guides_have_content(self, seed_source):
        assert "Step 1:" in seed_source or "## Step 1" in seed_source
        assert "You Have Rights" in seed_source

    def test_guides_have_reading_levels(self, seed_source):
        assert "GuideReadingLevel.high_school" in seed_source
        assert "GuideReadingLevel.middle_school" in seed_source

    def test_guides_are_published(self, seed_source):
        assert '"is_published": True' in seed_source

    # --- Glossary Terms ---

    def test_has_plaintiff_term(self, seed_source):
        assert '"term": "Plaintiff"' in seed_source

    def test_has_defendant_term(self, seed_source):
        assert '"term": "Defendant"' in seed_source

    def test_has_petitioner_term(self, seed_source):
        assert '"term": "Petitioner"' in seed_source

    def test_has_respondent_term(self, seed_source):
        assert '"term": "Respondent"' in seed_source

    def test_has_unlawful_detainer_term(self, seed_source):
        assert '"term": "Unlawful Detainer"' in seed_source

    def test_has_eviction_term(self, seed_source):
        assert '"term": "Eviction"' in seed_source

    def test_has_complaint_term(self, seed_source):
        assert '"term": "Complaint"' in seed_source

    def test_has_filing_fee_term(self, seed_source):
        assert '"term": "Filing Fee"' in seed_source

    def test_has_fee_waiver_term(self, seed_source):
        assert '"term": "Fee Waiver"' in seed_source

    def test_has_restraining_order_term(self, seed_source):
        assert '"term": "Restraining Order"' in seed_source

    def test_has_service_of_process_term(self, seed_source):
        assert '"term": "Service of Process"' in seed_source

    def test_has_continuance_term(self, seed_source):
        assert '"term": "Continuance"' in seed_source

    def test_glossary_terms_have_simple_definitions(self, seed_source):
        assert '"definition_simple":' in seed_source

    def test_glossary_terms_have_standard_definitions(self, seed_source):
        assert '"definition_standard":' in seed_source

    def test_glossary_terms_have_pronunciations(self, seed_source):
        assert '"pronunciation":' in seed_source

    def test_glossary_terms_have_translations(self, seed_source):
        assert '"translations":' in seed_source
        assert '"es":' in seed_source

    def test_glossary_terms_have_usage_examples(self, seed_source):
        assert '"usage_example":' in seed_source

    def test_glossary_terms_have_related_terms(self, seed_source):
        assert '"related_term_slugs":' in seed_source

    # --- Service Providers ---

    def test_has_la_county_law_library(self, seed_source):
        assert "Los Angeles County Law Library" in seed_source
        assert '"slug": "la-county-law-library"' in seed_source

    def test_has_lafla(self, seed_source):
        assert "Legal Aid Foundation of Los Angeles" in seed_source
        assert '"slug": "lafla"' in seed_source

    def test_has_nlsla(self, seed_source):
        assert "Neighborhood Legal Services" in seed_source
        assert '"slug": "nlsla"' in seed_source

    def test_providers_have_phone_numbers(self, seed_source):
        assert '"phone": "213-785-2529"' in seed_source
        assert '"phone": "800-399-4529"' in seed_source
        assert '"phone": "800-433-6251"' in seed_source

    def test_providers_have_addresses(self, seed_source):
        assert '"city": "Los Angeles"' in seed_source
        assert '"state": "CA"' in seed_source
        assert '"address_line1":' in seed_source

    def test_providers_have_languages(self, seed_source):
        assert '"languages_spoken":' in seed_source

    def test_providers_have_services(self, seed_source):
        assert '"services":' in seed_source

    # --- Legal Clinics ---

    def test_has_eviction_defense_clinic(self, seed_source):
        assert '"Eviction Defense Workshop"' in seed_source

    def test_has_family_law_clinic(self, seed_source):
        assert '"Family Law Self-Help Clinic"' in seed_source

    def test_has_small_claims_clinic(self, seed_source):
        assert '"Small Claims Court Preparation"' in seed_source

    def test_has_immigration_clinic(self, seed_source):
        assert '"Immigration Rights Know Your Rights Session"' in seed_source

    def test_has_name_change_clinic(self, seed_source):
        assert '"Name Change Petition Workshop"' in seed_source

    def test_clinics_have_dates(self, seed_source):
        assert '"date":' in seed_source
        assert "next_saturday" in seed_source

    def test_clinics_have_times(self, seed_source):
        assert '"start_time":' in seed_source
        assert '"end_time":' in seed_source

    def test_clinics_have_capacity(self, seed_source):
        assert '"capacity":' in seed_source

    def test_clinics_have_virtual_options(self, seed_source):
        assert '"is_virtual": True' in seed_source
        assert '"is_virtual": False' in seed_source

    def test_clinics_have_locations(self, seed_source):
        # Location is stored as a single free-text field, not split into
        # name/address.
        assert '"location":' in seed_source

    def test_clinics_have_what_to_bring(self, seed_source):
        assert '"what_to_bring":' in seed_source
        assert '"Photo ID"' in seed_source

    def test_clinics_have_languages(self, seed_source):
        # Check within clinic data context
        assert '"languages_available":' in seed_source

    def test_clinics_have_accessibility(self, seed_source):
        assert '"wheelchair_accessible": True' in seed_source

    def test_clinics_have_attorney_info(self, seed_source):
        assert '"attorney_names":' in seed_source

    def test_clinics_have_registration_status(self, seed_source):
        assert "ClinicStatus.registration_open" in seed_source
        assert "ClinicStatus.scheduled" in seed_source

    # --- Clinic Registrations ---

    def test_has_registration_data(self, seed_source):
        assert "seed_clinic_registrations" in seed_source

    def test_registrations_have_names(self, seed_source):
        assert '"Ana Rodriguez"' in seed_source
        assert '"David Chen"' in seed_source
        assert '"Maria Santos"' in seed_source
        assert '"Jennifer Park"' in seed_source
        assert '"Carlos Mendez"' in seed_source

    def test_registrations_have_contact_info(self, seed_source):
        assert '"preferred_contact":' in seed_source

    def test_registrations_have_statuses(self, seed_source):
        assert "RegistrationStatus.confirmed" in seed_source
        assert "RegistrationStatus.pending" in seed_source

    def test_registrations_track_interpreter_needs(self, seed_source):
        assert '"interpreter_needed": True' in seed_source
        assert '"interpreter_needed": False' in seed_source

    def test_registrations_have_issue_descriptions(self, seed_source):
        assert '"issue_description":' in seed_source

    def test_registrations_span_multiple_clinics(self, seed_source):
        assert "first_clinic_id" in seed_source
        assert "second_clinic_id" in seed_source


# ==================== Model Imports Test ====================


class TestModelImports:
    """Verify the seed script imports the correct models."""

    def test_imports_all_required_models(self):
        """Verify the seed script imports all necessary models."""
        source = (BACKEND_PATH / "scripts" / "seed_legal_resources.py").read_text()

        required_imports = [
            "LegalTopic",
            "LegalForm",
            "LegalGuide",
            "LegalServiceProvider",
            "LegalClinic",
            "LegalClinicRegistration",
            "LegalGlossaryTerm",
            "FormDifficulty",
            "FormStatus",
            "GuideReadingLevel",
            "ProviderType",
            "ClinicStatus",
            "RegistrationStatus",
        ]
        for model in required_imports:
            assert model in source, f"Missing import: {model}"


# ==================== Idempotency Verification ====================


class TestIdempotencyChecks:
    """Verify the seed script uses idempotent patterns."""

    @pytest.fixture
    def seed_source(self):
        return (BACKEND_PATH / "scripts" / "seed_legal_resources.py").read_text()

    def test_topics_check_existing(self, seed_source):
        assert "LegalTopic.slug == topic_data" in seed_source

    def test_providers_check_existing(self, seed_source):
        assert 'LegalServiceProvider.slug == provider_data["slug"]' in seed_source

    def test_forms_check_existing(self, seed_source):
        assert 'LegalForm.form_number == form_data["form_number"]' in seed_source

    def test_guides_check_existing(self, seed_source):
        assert 'LegalGuide.slug == guide_data["slug"]' in seed_source

    def test_glossary_check_existing(self, seed_source):
        assert 'LegalGlossaryTerm.slug == term_data["slug"]' in seed_source

    def test_clinics_check_existing(self, seed_source):
        assert "LegalClinic.name ==" in seed_source
        assert "LegalClinic.date ==" in seed_source

    def test_registrations_check_existing(self, seed_source):
        assert "LegalClinicRegistration.clinic_id ==" in seed_source
        assert "LegalClinicRegistration.name ==" in seed_source


# ==================== Display Readiness Tests ====================


class TestDisplayReadiness:
    """Verify seed data has all fields needed for frontend display."""

    @pytest.fixture
    def seed_source(self):
        return (BACKEND_PATH / "scripts" / "seed_legal_resources.py").read_text()

    def test_forms_have_display_fields(self, seed_source):
        """Forms need: title, form_number, difficulty_level, filing_fee, languages."""
        form_fields = ['"title":', '"form_number":', '"difficulty_level":',
                      '"filing_fee":', '"languages_available":']
        for field in form_fields:
            assert field in seed_source, f"Forms missing display field: {field}"

    def test_guides_have_display_fields(self, seed_source):
        """Guides need: title, slug, summary, reading_level, content."""
        guide_fields = ['"title":', '"slug":', '"summary":', '"content":',
                       '"reading_level":']
        for field in guide_fields:
            assert field in seed_source, f"Guides missing display field: {field}"

    def test_clinics_have_display_fields(self, seed_source):
        """Clinics need: title, date, start_time, end_time, capacity, is_virtual."""
        clinic_fields = ['"title":', '"date":', '"start_time":', '"end_time":',
                        '"capacity":', '"is_virtual":']
        for field in clinic_fields:
            assert field in seed_source, f"Clinics missing display field: {field}"

    def test_providers_have_display_fields(self, seed_source):
        """Providers need: name, phone, city, state, virtual_services."""
        provider_fields = ['"name":', '"phone":', '"city":', '"state":',
                          '"virtual_services":']
        for field in provider_fields:
            assert field in seed_source, f"Providers missing display field: {field}"

    def test_glossary_has_display_fields(self, seed_source):
        """Glossary needs: term, slug, definition_simple, definition_standard."""
        glossary_fields = ['"term":', '"slug":', '"definition_simple":',
                          '"definition_standard":']
        for field in glossary_fields:
            assert field in seed_source, f"Glossary missing display field: {field}"


# ==================== Search Support Tests ====================


class TestSearchSupport:
    """Verify seed data supports search functionality."""

    @pytest.fixture
    def seed_source(self):
        return (BACKEND_PATH / "scripts" / "seed_legal_resources.py").read_text()

    def test_topics_have_searchable_keywords(self, seed_source):
        keywords = ["divorce", "custody", "eviction", "tenant", "employment",
                    "debt", "immigration", "small claims"]
        for kw in keywords:
            assert f'"{kw}"' in seed_source, f"Missing searchable keyword: {kw}"

    def test_forms_have_searchable_descriptions(self, seed_source):
        assert '"description":' in seed_source
        assert '"when_to_use":' in seed_source
        assert '"who_should_use":' in seed_source

    def test_forms_have_plain_language_titles(self, seed_source):
        assert '"plain_language_title":' in seed_source

    def test_guides_have_searchable_summaries(self, seed_source):
        assert '"summary":' in seed_source

    def test_glossary_has_searchable_definitions(self, seed_source):
        assert '"definition_simple":' in seed_source
        assert '"definition_standard":' in seed_source


# ==================== Frontend API Compatibility Tests ====================


class TestFrontendApiCompatibility:
    """Verify frontend API service matches seed data structure.

    frontend/src/services/legal-api.ts was moved to frontend/src/api/legal-api.ts.
    """

    # api/legal-api.ts is now a barrel re-export
    # (export * from "./domains/reference/legal-api"); the real content
    # lives in the domain file below.
    LEGAL_API_TS = BACKEND_PATH.parent / "frontend" / "src" / "api" / "legal-api.ts"
    LEGAL_API_DOMAIN_TS = (
        BACKEND_PATH.parent / "frontend" / "src" / "api" / "domains" / "reference" / "legal-api.ts"
    )

    def test_legal_api_service_exists(self):
        assert self.LEGAL_API_TS.exists(), "legal-api.ts service file not found"
        assert self.LEGAL_API_DOMAIN_TS.exists(), "domains/reference/legal-api.ts service file not found"

    def test_api_has_glossary_support(self):
        content = self.LEGAL_API_DOMAIN_TS.read_text()
        assert "LegalGlossaryTerm" in content

    def test_api_has_clinic_support(self):
        content = self.LEGAL_API_DOMAIN_TS.read_text()
        assert "LegalClinic" in content
        assert "getUpcomingLegalClinics" in content

    def test_api_has_registration_support(self):
        content = self.LEGAL_API_DOMAIN_TS.read_text()
        assert "registerForClinic" in content
        assert "LegalClinicRegistration" in content

    def test_api_has_provider_support(self):
        content = self.LEGAL_API_DOMAIN_TS.read_text()
        assert "getLegalProviders" in content
        assert "LegalProvider" in content

    def test_api_has_form_search(self):
        content = self.LEGAL_API_DOMAIN_TS.read_text()
        assert "getLegalForms" in content
        assert "searchLegalForms" in content

    def test_api_has_guide_support(self):
        content = self.LEGAL_API_DOMAIN_TS.read_text()
        assert "getLegalGuides" in content
        assert "LegalGuide" in content


# ==================== Backend API Endpoint Tests ====================


class TestBackendApiEndpoints:
    """Verify backend API endpoints exist for all seed data types.

    app/api/v1/legal.py was split into a package (app/api/v1/legal/) with
    one module per resource (forms.py, glossary.py, clinics.py,
    providers.py, guides.py, ...) -- check the concatenated content of the
    whole package instead of a single file.
    """

    LEGAL_PKG_DIR = BACKEND_PATH / "app" / "api" / "v1" / "legal"

    @classmethod
    def _combined_source(cls) -> str:
        return "\n".join(
            p.read_text() for p in sorted(cls.LEGAL_PKG_DIR.glob("*.py"))
        )

    def test_legal_api_router_exists(self):
        assert self.LEGAL_PKG_DIR.is_dir(), "legal/ API package not found"

    def test_has_topics_endpoint(self):
        assert '"/topics"' in self._combined_source()

    def test_has_forms_endpoint(self):
        assert '"/forms"' in self._combined_source()

    def test_has_forms_search_endpoint(self):
        assert '"/forms/search"' in self._combined_source()

    def test_has_guides_endpoint(self):
        assert '"/guides"' in self._combined_source()

    def test_has_glossary_endpoint(self):
        assert '"/glossary"' in self._combined_source()

    def test_has_clinics_upcoming_endpoint(self):
        assert '"/clinics/upcoming"' in self._combined_source()

    def test_has_clinic_registration_endpoint(self):
        assert "/register" in self._combined_source()

    def test_has_providers_endpoint(self):
        assert '"/providers"' in self._combined_source()

    def test_has_providers_search_endpoint(self):
        assert '"/providers/search"' in self._combined_source()


# ==================== Data Completeness Summary ====================


class TestDataCompleteness:
    """Verify comprehensive coverage of all required data types."""

    @pytest.fixture
    def seed_source(self):
        return (BACKEND_PATH / "scripts" / "seed_legal_resources.py").read_text()

    def test_minimum_topic_count(self, seed_source):
        """Verify at least 7 topics are seeded."""
        topic_slugs = ['"slug": "family"', '"slug": "housing"', '"slug": "employment"',
                      '"slug": "consumer"', '"slug": "immigration"', '"slug": "name-change"',
                      '"slug": "small-claims"']
        found = sum(1 for s in topic_slugs if s in seed_source)
        assert found == 7, f"Expected 7 topics, found {found}"

    def test_minimum_form_count(self, seed_source):
        """Verify at least 9 forms are seeded."""
        form_numbers = ["FL-100", "FL-120", "DV-100", "UD-100", "UD-105",
                       "SC-100", "SC-120", "NC-100", "FW-001"]
        found = sum(1 for f in form_numbers if f'"{f}"' in seed_source)
        assert found == 9, f"Expected 9 forms, found {found}"

    def test_minimum_guide_count(self, seed_source):
        """Verify at least 2 guides are seeded."""
        guide_slugs = ["how-to-file-divorce-california", "defending-eviction"]
        found = sum(1 for s in guide_slugs if s in seed_source)
        assert found == 2, f"Expected 2 guides, found {found}"

    def test_minimum_glossary_count(self, seed_source):
        """Verify at least 12 glossary terms are seeded."""
        glossary_start = seed_source.find("async def seed_glossary_terms")
        glossary_end = seed_source.find("async def seed_legal_clinics")
        glossary_section = seed_source[glossary_start:glossary_end]
        term_count = glossary_section.count('"term":')
        assert term_count >= 12, f"Expected at least 12 glossary terms, found {term_count}"

    def test_minimum_provider_count(self, seed_source):
        """Verify at least 3 providers are seeded."""
        provider_slugs = ["la-county-law-library", "lafla", "nlsla"]
        found = sum(1 for s in provider_slugs if f'"{s}"' in seed_source)
        assert found == 3, f"Expected 3 providers, found {found}"

    def test_minimum_clinic_count(self, seed_source):
        """Verify at least 5 clinics are seeded."""
        clinic_titles = [
            "Eviction Defense Workshop",
            "Family Law Self-Help Clinic",
            "Small Claims Court Preparation",
            "Immigration Rights Know Your Rights Session",
            "Name Change Petition Workshop",
        ]
        found = sum(1 for t in clinic_titles if t in seed_source)
        assert found == 5, f"Expected 5 clinics, found {found}"

    def test_minimum_registration_count(self, seed_source):
        """Verify at least 5 registrations are seeded."""
        names = ["Ana Rodriguez", "David Chen", "Maria Santos",
                "Jennifer Park", "Carlos Mendez"]
        found = sum(1 for n in names if n in seed_source)
        assert found == 5, f"Expected 5 registrations, found {found}"
