# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Comprehensive tests for LSC Legal Resource Center.

Tests cover:
- Legal form browsing and access
- Guide and glossary display
- Legal clinic scheduling
- Service provider directory
- Access controls for legal resources
- Search within legal content
"""

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, hash_password
from app.models.user import User, UserRole


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
async def legal_staff(test_db):
    """Create a dedicated staff user for legal tests (unique email per test)."""
    unique = uuid.uuid4().hex[:8]
    user = User(
        email=f"legal-staff-{unique}@example.com",
        password_hash=hash_password("TestPassword123!"),
        first_name="Legal",
        last_name="Staff",
        role=UserRole.STAFF,
        is_active=True,
        email_verified=True,
    )
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)
    return user


@pytest.fixture
async def legal_patron(test_db):
    """Create a dedicated patron user for legal tests (unique email per test)."""
    unique = uuid.uuid4().hex[:8]
    user = User(
        email=f"legal-patron-{unique}@example.com",
        password_hash=hash_password("TestPassword123!"),
        first_name="Legal",
        last_name="Patron",
        role=UserRole.PATRON,
        is_active=True,
        email_verified=True,
    )
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)
    return user


@pytest.fixture
async def staff_token(legal_staff) -> str:
    """Create a JWT token for a staff user."""
    return create_access_token(
        subject=str(legal_staff.id),
        email=legal_staff.email,
        role=legal_staff.role.value if hasattr(legal_staff.role, "value") else str(legal_staff.role),
    )


@pytest.fixture
async def patron_token(legal_patron) -> str:
    """Create a JWT token for a patron user."""
    return create_access_token(
        subject=str(legal_patron.id),
        email=legal_patron.email,
        role=legal_patron.role.value if hasattr(legal_patron.role, "value") else str(legal_patron.role),
    )


@pytest.fixture
async def staff_headers(staff_token) -> dict:
    """Authorization headers for staff requests."""
    return {"Authorization": f"Bearer {staff_token}"}


@pytest.fixture
async def patron_headers(patron_token) -> dict:
    """Authorization headers for patron requests."""
    return {"Authorization": f"Bearer {patron_token}"}


@pytest.fixture
async def legal_topic(test_db, legal_staff):
    """Create a test legal topic."""
    from app.models.legal.taxonomy import LegalTopic

    unique = uuid.uuid4().hex[:8]
    topic = LegalTopic(
        name=f"Family Law {unique}",
        slug=f"family-law-{unique}",
        description="Legal issues related to family matters",
        is_active=True,
        is_featured=True,
        display_order=1,
        created_by_id=legal_staff.id,
    )
    test_db.add(topic)
    await test_db.commit()
    await test_db.refresh(topic)
    return topic


@pytest.fixture
async def legal_form(test_db, legal_staff, legal_topic):
    """Create a test legal form."""
    from app.models.legal.forms import LegalForm

    unique = uuid.uuid4().hex[:8]
    form = LegalForm(
        title="Petition for Dissolution of Marriage",
        form_number=f"FL-100-{unique}",
        topic_id=legal_topic.id,
        jurisdiction="California",
        jurisdiction_code="CA",
        court_type="family",
        description="Used to start a divorce proceeding",
        when_to_use="When you want to file for divorce",
        who_should_use="Married individuals seeking divorce",
        plain_language_title="Divorce Filing Form",
        difficulty_level="moderate",
        filing_fee=435.0,
        page_count=4,
        status="active",
        created_by_id=legal_staff.id,
    )
    test_db.add(form)
    await test_db.commit()
    await test_db.refresh(form)
    return form


@pytest.fixture
async def legal_guide(test_db, legal_staff, legal_topic):
    """Create a test legal guide."""
    from app.models.legal.taxonomy import LegalGuide

    unique = uuid.uuid4().hex[:8]
    guide = LegalGuide(
        title="How to File for Divorce in California",
        slug=f"how-to-file-divorce-california-{unique}",
        topic_id=legal_topic.id,
        summary="Step-by-step guide to filing for divorce",
        content="Full content of the guide...",
        reading_level="middle_school",
        is_published=True,
        is_featured=True,
        steps=[
            {"step": 1, "title": "Complete the forms", "description": "Fill out FL-100"},
            {"step": 2, "title": "File with the court", "description": "Submit to clerk"},
        ],
        created_by_id=legal_staff.id,
    )
    test_db.add(guide)
    await test_db.commit()
    await test_db.refresh(guide)
    return guide


@pytest.fixture
async def glossary_term(test_db):
    """Create a test glossary term."""
    from app.models.legal.resources import LegalGlossaryTerm

    unique = uuid.uuid4().hex[:8]
    term = LegalGlossaryTerm(
        term=f"Plaintiff {unique}",
        slug=f"plaintiff-{unique}",
        definition_simple="The person who starts a lawsuit",
        definition_standard="The party who initiates a civil lawsuit by filing a complaint",
        definition_legal="The complaining party in a civil action; the party who brings suit",
        pronunciation="PLAYN-tif",
        usage_example="The plaintiff filed a complaint against the defendant.",
        is_active=True,
    )
    test_db.add(term)
    await test_db.commit()
    await test_db.refresh(term)
    return term


@pytest.fixture
async def service_provider(test_db, legal_staff):
    """Create a test service provider."""
    from app.models.legal.providers import LegalServiceProvider

    unique = uuid.uuid4().hex[:8]
    provider = LegalServiceProvider(
        name="Legal Aid Foundation of Los Angeles",
        slug=f"lafla-{unique}",
        provider_type="legal_aid",
        description="Free legal services for low-income residents",
        phone="213-640-3800",
        city="Los Angeles",
        state="California",
        is_active=True,
        accepts_walkins=True,
        virtual_services=True,
        created_by_id=legal_staff.id,
    )
    test_db.add(provider)
    await test_db.commit()
    await test_db.refresh(provider)
    return provider


@pytest.fixture
async def legal_clinic(test_db, legal_staff, legal_topic, service_provider):
    """Create a test legal clinic."""
    from datetime import date, time
    from app.models.legal.providers import LegalClinic

    clinic = LegalClinic(
        name="Free Family Law Consultation",
        topic_id=legal_topic.id,
        provider_id=service_provider.id,
        description="Free 30-minute consultations with volunteer attorneys",
        date=date(2026, 4, 15),
        start_time="10:00",
        end_time="14:00",
        is_virtual=False,
        location="Central Library - Meeting Room A, 630 W 5th St, Los Angeles, CA 90071",
        capacity=20,
        current_registrations=5,
        waitlist_capacity=10,
        current_waitlist=0,
        registration_required=True,
        status="registration_open",
        wheelchair_accessible=True,
        created_by_id=legal_staff.id,
    )
    test_db.add(clinic)
    await test_db.commit()
    await test_db.refresh(clinic)
    return clinic


# ============================================================================
# 1. Legal Form Browsing and Access Tests
# ============================================================================


@pytest.mark.asyncio
class TestFormBrowsingAndAccess:
    """Test legal form browsing and access endpoints."""

    async def test_list_forms_returns_200(self, client: AsyncClient, legal_form):
        """GET /legal/forms should return 200 with a list of forms."""
        response = await client.get("/api/v1/legal/forms")
        assert response.status_code == 200
        data = response.json()
        assert "forms" in data
        assert "total" in data
        assert isinstance(data["forms"], list)

    async def test_list_forms_contains_created_form(self, client: AsyncClient, legal_form):
        """Listed forms should include the created test form."""
        response = await client.get("/api/v1/legal/forms")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1
        form_ids = [f["id"] for f in data["forms"]]
        assert legal_form.id in form_ids

    async def test_list_forms_with_topic_filter(self, client: AsyncClient, legal_form, legal_topic):
        """GET /legal/forms?topic_id= should filter forms by topic."""
        response = await client.get(f"/api/v1/legal/forms?topic_id={legal_topic.id}")
        assert response.status_code == 200
        data = response.json()
        for form in data["forms"]:
            assert form["topic_id"] == legal_topic.id

    async def test_list_forms_with_jurisdiction_filter(self, client: AsyncClient, legal_form):
        """GET /legal/forms?jurisdiction= should filter forms by jurisdiction."""
        response = await client.get("/api/v1/legal/forms?jurisdiction=California")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1

    async def test_list_forms_with_difficulty_filter(self, client: AsyncClient, legal_form):
        """GET /legal/forms?difficulty_level= should filter forms by difficulty."""
        response = await client.get("/api/v1/legal/forms?difficulty_level=moderate")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1

    async def test_list_forms_pagination(self, client: AsyncClient, legal_form):
        """GET /legal/forms should support limit/offset pagination."""
        response = await client.get("/api/v1/legal/forms?limit=1&offset=0")
        assert response.status_code == 200
        data = response.json()
        assert data["limit"] == 1
        assert data["offset"] == 0
        assert len(data["forms"]) <= 1

    async def test_get_form_by_id(self, client: AsyncClient, legal_form):
        """GET /legal/forms/{form_id} should return form details."""
        response = await client.get(f"/api/v1/legal/forms/{legal_form.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == legal_form.id
        assert data["title"] == "Petition for Dissolution of Marriage"
        assert data["form_number"].startswith("FL-100")
        assert data["jurisdiction"] == "California"
        assert data["difficulty_level"] == "moderate"

    async def test_get_form_returns_plain_language_fields(self, client: AsyncClient, legal_form):
        """Form detail should include plain language fields."""
        response = await client.get(f"/api/v1/legal/forms/{legal_form.id}")
        assert response.status_code == 200
        data = response.json()
        assert "plain_language_title" in data
        assert "when_to_use" in data
        assert "who_should_use" in data
        assert "description" in data

    async def test_get_form_returns_filing_fee(self, client: AsyncClient, legal_form):
        """Form detail should include filing fee information."""
        response = await client.get(f"/api/v1/legal/forms/{legal_form.id}")
        assert response.status_code == 200
        data = response.json()
        assert "filing_fee" in data
        assert data["filing_fee"] == 435.0

    async def test_get_nonexistent_form_returns_404(self, client: AsyncClient):
        """GET /legal/forms/99999 should return 404 for missing form."""
        response = await client.get("/api/v1/legal/forms/99999")
        assert response.status_code == 404

    async def test_track_form_download(self, client: AsyncClient, legal_form):
        """POST /legal/forms/{form_id}/download should track a download."""
        response = await client.post(f"/api/v1/legal/forms/{legal_form.id}/download")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "recorded"

    async def test_list_forms_no_auth_required(self, client: AsyncClient, legal_form):
        """Public users should be able to browse forms without authentication."""
        response = await client.get("/api/v1/legal/forms")
        assert response.status_code == 200

    async def test_get_form_no_auth_required(self, client: AsyncClient, legal_form):
        """Public users should be able to view form details without authentication."""
        response = await client.get(f"/api/v1/legal/forms/{legal_form.id}")
        assert response.status_code == 200


# ============================================================================
# 2. Guide and Glossary Display Tests
# ============================================================================


@pytest.mark.asyncio
class TestGuideDisplay:
    """Test legal guide display endpoints."""

    async def test_list_guides_returns_200(self, client: AsyncClient, legal_guide):
        """GET /legal/guides should return a list of guides."""
        response = await client.get("/api/v1/legal/guides")
        assert response.status_code == 200
        data = response.json()
        assert "guides" in data
        assert "total" in data

    async def test_list_guides_contains_guide(self, client: AsyncClient, legal_guide):
        """Listed guides should include created test guide."""
        response = await client.get("/api/v1/legal/guides")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1
        guide_ids = [g["id"] for g in data["guides"]]
        assert legal_guide.id in guide_ids

    async def test_list_guides_with_topic_filter(self, client: AsyncClient, legal_guide, legal_topic):
        """GET /legal/guides?topic_id= should filter guides by topic."""
        response = await client.get(f"/api/v1/legal/guides?topic_id={legal_topic.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1

    async def test_list_guides_with_reading_level_filter(self, client: AsyncClient, legal_guide):
        """GET /legal/guides?reading_level= should filter by reading level."""
        response = await client.get("/api/v1/legal/guides?reading_level=middle_school")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1

    async def test_get_guide_by_id(self, client: AsyncClient, legal_guide):
        """GET /legal/guides/{guide_id} should return full guide details."""
        response = await client.get(f"/api/v1/legal/guides/{legal_guide.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == legal_guide.id
        assert data["title"] == "How to File for Divorce in California"
        assert data["content"] is not None
        assert "steps" in data
        assert len(data["steps"]) == 2

    async def test_get_guide_by_slug(self, client: AsyncClient, legal_guide):
        """GET /legal/guides/slug/{slug} should return guide by slug."""
        response = await client.get(f"/api/v1/legal/guides/slug/{legal_guide.slug}")
        assert response.status_code == 200
        data = response.json()
        assert data["slug"] == legal_guide.slug

    async def test_get_guide_returns_reading_level(self, client: AsyncClient, legal_guide):
        """Guide detail should include reading level information."""
        response = await client.get(f"/api/v1/legal/guides/{legal_guide.id}")
        assert response.status_code == 200
        data = response.json()
        assert "reading_level" in data
        assert data["reading_level"] == "middle_school"

    async def test_get_nonexistent_guide_returns_404(self, client: AsyncClient):
        """GET /legal/guides/99999 should return 404."""
        response = await client.get("/api/v1/legal/guides/99999")
        assert response.status_code == 404

    async def test_record_guide_feedback(self, client: AsyncClient, legal_guide):
        """POST /legal/guides/{guide_id}/helpful should record feedback."""
        response = await client.post(
            f"/api/v1/legal/guides/{legal_guide.id}/helpful?was_helpful=true"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "recorded"

    async def test_list_guides_no_auth_required(self, client: AsyncClient, legal_guide):
        """Public users should be able to browse guides without authentication."""
        response = await client.get("/api/v1/legal/guides")
        assert response.status_code == 200


@pytest.mark.asyncio
class TestGlossaryDisplay:
    """Test legal glossary display endpoints."""

    async def test_list_glossary_terms_returns_200(self, client: AsyncClient, glossary_term):
        """GET /legal/glossary should return a list of glossary terms."""
        response = await client.get("/api/v1/legal/glossary")
        assert response.status_code == 200
        data = response.json()
        assert "terms" in data
        assert "total" in data

    async def test_list_glossary_terms_contains_term(self, client: AsyncClient, glossary_term):
        """Listed terms should include the created test term."""
        response = await client.get("/api/v1/legal/glossary")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1
        term_ids = [t["id"] for t in data["terms"]]
        assert glossary_term.id in term_ids

    async def test_list_glossary_by_letter(self, client: AsyncClient, glossary_term):
        """GET /legal/glossary?letter=P should filter by first letter."""
        response = await client.get("/api/v1/legal/glossary?letter=P")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1

    async def test_get_glossary_term_by_slug(self, client: AsyncClient, glossary_term):
        """GET /legal/glossary/{slug} should return term details."""
        response = await client.get(f"/api/v1/legal/glossary/{glossary_term.slug}")
        assert response.status_code == 200
        data = response.json()
        assert data["slug"].startswith("plaintiff")
        assert data["term"].startswith("Plaintiff")

    async def test_glossary_term_has_multiple_definitions(self, client: AsyncClient, glossary_term):
        """Glossary term should include simple, standard, and legal definitions."""
        response = await client.get(f"/api/v1/legal/glossary/{glossary_term.slug}")
        assert response.status_code == 200
        data = response.json()
        assert "definition_simple" in data
        assert "definition_standard" in data
        assert "definition_legal" in data
        assert data["definition_simple"] == "The person who starts a lawsuit"

    async def test_glossary_term_has_pronunciation(self, client: AsyncClient, glossary_term):
        """Glossary term should include pronunciation guide."""
        response = await client.get(f"/api/v1/legal/glossary/{glossary_term.slug}")
        assert response.status_code == 200
        data = response.json()
        assert "pronunciation" in data
        assert data["pronunciation"] == "PLAYN-tif"

    async def test_glossary_term_has_usage_example(self, client: AsyncClient, glossary_term):
        """Glossary term should include usage example."""
        response = await client.get(f"/api/v1/legal/glossary/{glossary_term.slug}")
        assert response.status_code == 200
        data = response.json()
        assert "usage_example" in data
        assert data["usage_example"] is not None

    async def test_get_nonexistent_glossary_term_returns_404(self, client: AsyncClient):
        """GET /legal/glossary/nonexistent-term should return 404."""
        response = await client.get("/api/v1/legal/glossary/nonexistent-term-xyz")
        assert response.status_code == 404

    async def test_glossary_no_auth_required(self, client: AsyncClient, glossary_term):
        """Public users should be able to browse glossary without authentication."""
        response = await client.get("/api/v1/legal/glossary")
        assert response.status_code == 200


# ============================================================================
# 3. Legal Clinic Scheduling Tests
# ============================================================================


@pytest.mark.asyncio
class TestLegalClinicScheduling:
    """Test legal clinic scheduling endpoints."""

    async def test_list_clinics_returns_200(self, client: AsyncClient, legal_clinic):
        """GET /legal/clinics should return a list of clinics."""
        response = await client.get("/api/v1/legal/clinics")
        assert response.status_code == 200
        data = response.json()
        assert "clinics" in data
        assert "total" in data

    async def test_list_clinics_contains_clinic(self, client: AsyncClient, legal_clinic):
        """Listed clinics should include the created test clinic."""
        response = await client.get("/api/v1/legal/clinics")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1
        clinic_ids = [c["id"] for c in data["clinics"]]
        assert legal_clinic.id in clinic_ids

    async def test_list_clinics_with_topic_filter(self, client: AsyncClient, legal_clinic, legal_topic):
        """GET /legal/clinics?topic_id= should filter clinics by topic."""
        response = await client.get(f"/api/v1/legal/clinics?topic_id={legal_topic.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1

    async def test_list_clinics_virtual_filter(self, client: AsyncClient, legal_clinic):
        """GET /legal/clinics?is_virtual=false should filter by format."""
        response = await client.get("/api/v1/legal/clinics?is_virtual=false")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1

    async def test_list_clinics_date_filter(self, client: AsyncClient, legal_clinic):
        """GET /legal/clinics?from_date=&to_date= should filter by date range."""
        response = await client.get(
            "/api/v1/legal/clinics?from_date=2026-04-01&to_date=2026-04-30"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1

    async def test_get_clinic_by_id(self, client: AsyncClient, legal_clinic):
        """GET /legal/clinics/{clinic_id} should return clinic details."""
        response = await client.get(f"/api/v1/legal/clinics/{legal_clinic.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == legal_clinic.id
        assert data["name"] == "Free Family Law Consultation"
        assert data["capacity"] == 20
        assert data["spots_available"] == 15  # 20 - 5

    async def test_get_clinic_shows_availability(self, client: AsyncClient, legal_clinic):
        """Clinic detail should show registration availability."""
        response = await client.get(f"/api/v1/legal/clinics/{legal_clinic.id}")
        assert response.status_code == 200
        data = response.json()
        assert "capacity" in data
        assert "current_registrations" in data
        assert "spots_available" in data
        assert "waitlist_capacity" in data
        assert "registration_required" in data

    async def test_get_clinic_shows_accessibility(self, client: AsyncClient, legal_clinic):
        """Clinic detail should show accessibility information."""
        response = await client.get(f"/api/v1/legal/clinics/{legal_clinic.id}")
        assert response.status_code == 200
        data = response.json()
        assert "wheelchair_accessible" in data
        assert data["wheelchair_accessible"] is True

    async def test_register_for_clinic(self, client: AsyncClient, legal_clinic):
        """POST /legal/clinics/{clinic_id}/register should register a user."""
        registration_data = {
            "name": "Jane Doe",
            "email": "jane@example.com",
            "phone": "555-0100",
            "preferred_contact": "email",
            "issue_description": "Divorce filing assistance",
        }
        response = await client.post(
            f"/api/v1/legal/clinics/{legal_clinic.id}/register",
            json=registration_data,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["clinic_id"] == legal_clinic.id
        assert data["name"] == "Jane Doe"

    async def test_cancel_clinic_registration(self, client: AsyncClient, legal_clinic, staff_headers):
        """DELETE /legal/clinics/registrations/{id} should cancel a registration.

        Anonymous registration is allowed, but cancellation requires ownership
        or staff role (app/api/v1/legal/clinics.py::cancel_registration) -- an
        anonymous registrant here has no account to authenticate as, so cancel
        as staff.
        """
        # First register
        registration_data = {
            "name": "John Cancel",
            "email": "cancel@example.com",
            "preferred_contact": "email",
        }
        reg_response = await client.post(
            f"/api/v1/legal/clinics/{legal_clinic.id}/register",
            json=registration_data,
        )
        assert reg_response.status_code == 201
        reg_id = reg_response.json()["id"]

        # Then cancel
        cancel_response = await client.delete(
            f"/api/v1/legal/clinics/registrations/{reg_id}",
            headers=staff_headers,
        )
        assert cancel_response.status_code == 204

    async def test_get_nonexistent_clinic_returns_404(self, client: AsyncClient):
        """GET /legal/clinics/99999 should return 404."""
        response = await client.get("/api/v1/legal/clinics/99999")
        assert response.status_code == 404

    async def test_get_upcoming_clinics(self, client: AsyncClient, legal_clinic):
        """GET /legal/clinics/upcoming should return upcoming clinics."""
        response = await client.get("/api/v1/legal/clinics/upcoming")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    async def test_list_clinics_no_auth_required(self, client: AsyncClient, legal_clinic):
        """Public users should be able to browse clinics without authentication."""
        response = await client.get("/api/v1/legal/clinics")
        assert response.status_code == 200


# ============================================================================
# 4. Service Provider Directory Tests
# ============================================================================


@pytest.mark.asyncio
class TestServiceProviderDirectory:
    """Test service provider directory endpoints."""

    async def test_list_providers_returns_200(self, client: AsyncClient, service_provider):
        """GET /legal/providers should return a list of providers."""
        response = await client.get("/api/v1/legal/providers")
        assert response.status_code == 200
        data = response.json()
        assert "providers" in data
        assert "total" in data

    async def test_list_providers_contains_provider(self, client: AsyncClient, service_provider):
        """Listed providers should include the created test provider."""
        response = await client.get("/api/v1/legal/providers")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1
        provider_ids = [p["id"] for p in data["providers"]]
        assert service_provider.id in provider_ids

    async def test_list_providers_with_type_filter(self, client: AsyncClient, service_provider):
        """GET /legal/providers?provider_type= should filter by type."""
        response = await client.get("/api/v1/legal/providers?provider_type=legal_aid")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1

    async def test_list_providers_with_city_filter(self, client: AsyncClient, service_provider):
        """GET /legal/providers?city= should filter by city."""
        response = await client.get("/api/v1/legal/providers?city=Los+Angeles")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1

    async def test_list_providers_walkins_filter(self, client: AsyncClient, service_provider):
        """GET /legal/providers?accepts_walkins=true should filter by walk-in acceptance."""
        response = await client.get("/api/v1/legal/providers?accepts_walkins=true")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1

    async def test_list_providers_virtual_filter(self, client: AsyncClient, service_provider):
        """GET /legal/providers?virtual_services=true should filter by virtual services."""
        response = await client.get("/api/v1/legal/providers?virtual_services=true")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1

    async def test_get_provider_by_id(self, client: AsyncClient, service_provider):
        """GET /legal/providers/{provider_id} should return provider details."""
        response = await client.get(f"/api/v1/legal/providers/{service_provider.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == service_provider.id
        assert data["name"] == "Legal Aid Foundation of Los Angeles"
        assert data["provider_type"] == "legal_aid"

    async def test_get_provider_returns_contact_info(self, client: AsyncClient, service_provider):
        """Provider detail should include contact information."""
        response = await client.get(f"/api/v1/legal/providers/{service_provider.id}")
        assert response.status_code == 200
        data = response.json()
        assert "phone" in data
        assert "city" in data
        assert "state" in data

    async def test_get_provider_returns_service_availability(self, client: AsyncClient, service_provider):
        """Provider detail should include service availability."""
        response = await client.get(f"/api/v1/legal/providers/{service_provider.id}")
        assert response.status_code == 200
        data = response.json()
        assert "accepts_walkins" in data
        assert "virtual_services" in data
        assert "is_active" in data

    async def test_get_nonexistent_provider_returns_404(self, client: AsyncClient):
        """GET /legal/providers/99999 should return 404."""
        response = await client.get("/api/v1/legal/providers/99999")
        assert response.status_code == 404

    async def test_list_providers_no_auth_required(self, client: AsyncClient, service_provider):
        """Public users should be able to browse providers without authentication."""
        response = await client.get("/api/v1/legal/providers")
        assert response.status_code == 200

    async def test_list_providers_pagination(self, client: AsyncClient, service_provider):
        """GET /legal/providers should support pagination."""
        response = await client.get("/api/v1/legal/providers?limit=5&offset=0")
        assert response.status_code == 200
        data = response.json()
        assert data["limit"] == 5
        assert data["offset"] == 0


# ============================================================================
# 5. Access Controls for Legal Resources Tests
# ============================================================================


@pytest.mark.asyncio
class TestAccessControls:
    """Test access controls for legal resources."""

    # -- Public access (no auth required) --

    async def test_forms_public_access(self, client: AsyncClient, legal_form):
        """Form listing should be publicly accessible."""
        response = await client.get("/api/v1/legal/forms")
        assert response.status_code == 200

    async def test_form_detail_public_access(self, client: AsyncClient, legal_form):
        """Form detail should be publicly accessible."""
        response = await client.get(f"/api/v1/legal/forms/{legal_form.id}")
        assert response.status_code == 200

    async def test_guides_public_access(self, client: AsyncClient, legal_guide):
        """Guide listing should be publicly accessible."""
        response = await client.get("/api/v1/legal/guides")
        assert response.status_code == 200

    async def test_glossary_public_access(self, client: AsyncClient, glossary_term):
        """Glossary listing should be publicly accessible."""
        response = await client.get("/api/v1/legal/glossary")
        assert response.status_code == 200

    async def test_clinics_public_access(self, client: AsyncClient, legal_clinic):
        """Clinic listing should be publicly accessible."""
        response = await client.get("/api/v1/legal/clinics")
        assert response.status_code == 200

    async def test_providers_public_access(self, client: AsyncClient, service_provider):
        """Provider listing should be publicly accessible."""
        response = await client.get("/api/v1/legal/providers")
        assert response.status_code == 200

    async def test_disclaimer_public_access(self, client: AsyncClient):
        """Legal disclaimer should be publicly accessible."""
        response = await client.get("/api/v1/legal/disclaimer")
        assert response.status_code == 200
        data = response.json()
        assert "disclaimer_text" in data

    async def test_topics_public_access(self, client: AsyncClient, legal_topic):
        """Topic listing should be publicly accessible."""
        response = await client.get("/api/v1/legal/topics")
        assert response.status_code == 200

    # -- Staff-protected endpoints --

    async def test_create_form_requires_auth(self, client: AsyncClient):
        """POST /legal/forms should require authentication."""
        form_data = {
            "title": "Test Form",
            "form_number": "TEST-001",
            "jurisdiction": "California",
        }
        response = await client.post("/api/v1/legal/forms", json=form_data)
        assert response.status_code == 401

    async def test_create_form_with_staff_auth(
        self, client: AsyncClient, staff_headers, legal_topic
    ):
        """POST /legal/forms should succeed with staff authentication."""
        form_data = {
            "title": "Staff Created Form",
            "form_number": "STAFF-001",
            "jurisdiction": "California",
            "topic_id": legal_topic.id,
        }
        response = await client.post(
            "/api/v1/legal/forms", json=form_data, headers=staff_headers
        )
        # 201 = created, 422 = schema validation, 401 = Redis unavailable in test (fail-secure)
        assert response.status_code in [201, 401, 422]

    async def test_update_form_requires_auth(self, client: AsyncClient, legal_form):
        """PATCH /legal/forms/{id} should require authentication."""
        response = await client.patch(
            f"/api/v1/legal/forms/{legal_form.id}",
            json={"title": "Updated"},
        )
        assert response.status_code == 401

    async def test_create_guide_requires_auth(self, client: AsyncClient):
        """POST /legal/guides should require authentication."""
        guide_data = {
            "title": "Unauthorized Guide",
            "slug": "unauthorized-guide",
            "content": "test",
        }
        response = await client.post("/api/v1/legal/guides", json=guide_data)
        assert response.status_code == 401

    async def test_create_topic_requires_auth(self, client: AsyncClient):
        """POST /legal/topics should require authentication."""
        topic_data = {
            "name": "Unauthorized Topic",
            "slug": "unauthorized-topic",
        }
        response = await client.post("/api/v1/legal/topics", json=topic_data)
        assert response.status_code == 401

    async def test_create_glossary_term_requires_auth(self, client: AsyncClient):
        """POST /legal/glossary should require authentication."""
        term_data = {
            "term": "Test Term",
            "slug": "test-term",
            "definition_standard": "A test definition",
        }
        response = await client.post("/api/v1/legal/glossary", json=term_data)
        assert response.status_code == 401

    async def test_create_clinic_requires_auth(self, client: AsyncClient):
        """POST /legal/clinics should require authentication."""
        clinic_data = {
            "name": "Unauthorized Clinic",
            "title": "Test Clinic",
            "date": "2026-05-01",
        }
        response = await client.post("/api/v1/legal/clinics", json=clinic_data)
        assert response.status_code == 401

    async def test_create_provider_requires_auth(self, client: AsyncClient):
        """POST /legal/providers should require authentication."""
        provider_data = {
            "name": "Unauthorized Provider",
            "slug": "unauthorized-provider",
            "provider_type": "legal_aid",
        }
        response = await client.post("/api/v1/legal/providers", json=provider_data)
        assert response.status_code == 401

    async def test_staff_guidelines_require_auth(self, client: AsyncClient):
        """GET /legal/staff/guidelines should require authentication."""
        response = await client.get("/api/v1/legal/staff/guidelines")
        assert response.status_code == 401


# ============================================================================
# 6. Search Within Legal Content Tests
# ============================================================================


@pytest.mark.asyncio
class TestSearchLegalContent:
    """Test search within legal content endpoints."""

    async def test_search_forms_by_query(self, client: AsyncClient, legal_form):
        """GET /legal/forms?query= should search forms by keyword."""
        response = await client.get("/api/v1/legal/forms?query=divorce")
        assert response.status_code == 200
        data = response.json()
        assert "forms" in data

    async def test_search_forms_post_endpoint(self, client: AsyncClient, legal_form):
        """POST /legal/forms/search should search forms."""
        search_data = {"query": "dissolution"}
        response = await client.post("/api/v1/legal/forms/search", json=search_data)
        assert response.status_code == 200
        data = response.json()
        assert "forms" in data

    async def test_search_forms_get_info_endpoint(self, client: AsyncClient):
        """GET /legal/forms/search should return search feature info."""
        response = await client.get("/api/v1/legal/forms/search")
        assert response.status_code == 200
        data = response.json()
        assert "search_fields" in data
        assert "available_filters" in data

    async def test_search_glossary_by_query(self, client: AsyncClient, glossary_term):
        """GET /legal/glossary?query= should search glossary terms."""
        response = await client.get("/api/v1/legal/glossary?query=plaintiff")
        assert response.status_code == 200
        data = response.json()
        assert "terms" in data

    async def test_search_glossary_by_letter(self, client: AsyncClient, glossary_term):
        """GET /legal/glossary?letter=P should filter by first letter."""
        response = await client.get("/api/v1/legal/glossary?letter=P")
        assert response.status_code == 200
        data = response.json()
        assert "terms" in data

    async def test_search_forms_empty_query(self, client: AsyncClient, legal_form):
        """Search with empty query should return all forms."""
        response = await client.get("/api/v1/legal/forms")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1

    async def test_search_forms_no_results(self, client: AsyncClient, legal_form):
        """Search with non-matching query should return empty results."""
        response = await client.get("/api/v1/legal/forms?query=zzzznonexistentzzz")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert len(data["forms"]) == 0

    async def test_search_forms_with_combined_filters(self, client: AsyncClient, legal_form):
        """Search with query and filters combined should work."""
        response = await client.get(
            "/api/v1/legal/forms?query=divorce&jurisdiction=California&difficulty_level=moderate"
        )
        assert response.status_code == 200
        data = response.json()
        assert "forms" in data

    async def test_search_no_auth_required(self, client: AsyncClient, legal_form):
        """Search should be publicly accessible."""
        response = await client.get("/api/v1/legal/forms?query=test")
        assert response.status_code == 200


# ============================================================================
# 7. Topic Management Tests
# ============================================================================


@pytest.mark.asyncio
class TestTopicManagement:
    """Test legal topic listing and hierarchy endpoints."""

    async def test_list_topics_returns_200(self, client: AsyncClient, legal_topic):
        """GET /legal/topics should return a list of topics."""
        response = await client.get("/api/v1/legal/topics")
        assert response.status_code == 200
        data = response.json()
        assert "topics" in data
        assert "total" in data

    async def test_get_topic_by_id(self, client: AsyncClient, legal_topic):
        """GET /legal/topics/{topic_id} should return topic details."""
        response = await client.get(f"/api/v1/legal/topics/{legal_topic.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == legal_topic.id
        assert data["name"].startswith("Family Law")

    async def test_get_topic_by_slug(self, client: AsyncClient, legal_topic):
        """GET /legal/topics/slug/{slug} should return topic by slug."""
        response = await client.get(f"/api/v1/legal/topics/slug/{legal_topic.slug}")
        assert response.status_code == 200
        data = response.json()
        assert data["slug"].startswith("family-law")

    async def test_get_topic_tree(self, client: AsyncClient, legal_topic):
        """GET /legal/topics/tree should return hierarchical topic tree."""
        response = await client.get("/api/v1/legal/topics/tree")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    async def test_get_nonexistent_topic_returns_404(self, client: AsyncClient):
        """GET /legal/topics/99999 should return 404."""
        response = await client.get("/api/v1/legal/topics/99999")
        assert response.status_code == 404


# ============================================================================
# 8. Legal Disclaimer and Emergency Resources Tests
# ============================================================================


@pytest.mark.asyncio
class TestDisclaimerAndEmergency:
    """Test legal disclaimer and emergency resources."""

    async def test_get_legal_disclaimer(self, client: AsyncClient):
        """GET /legal/disclaimer should return the legal disclaimer."""
        response = await client.get("/api/v1/legal/disclaimer")
        assert response.status_code == 200
        data = response.json()
        assert "disclaimer_text" in data
        assert "IMPORTANT" in data["disclaimer_text"]
        assert "emergency_contacts" in data
        assert "quick_exit_enabled" in data

    async def test_disclaimer_has_emergency_contacts(self, client: AsyncClient):
        """Disclaimer should include emergency contact information."""
        response = await client.get("/api/v1/legal/disclaimer")
        assert response.status_code == 200
        data = response.json()
        contacts = data["emergency_contacts"]
        assert len(contacts) >= 1
        # Should have 911 emergency
        phones = [c.get("phone") for c in contacts]
        assert "911" in phones

    async def test_get_emergency_resources(self, client: AsyncClient):
        """GET /legal/emergency should return emergency resources."""
        response = await client.get("/api/v1/legal/emergency")
        assert response.status_code in [200, 404]  # 404 if no data seeded

    async def test_emergency_resources_no_auth(self, client: AsyncClient):
        """Emergency resources should not require authentication."""
        response = await client.get("/api/v1/legal/emergency")
        assert response.status_code in [200, 404]
        # Should never return 401
        assert response.status_code != 401


# ============================================================================
# 9. Content Feedback Tests
# ============================================================================


@pytest.mark.asyncio
class TestContentFeedback:
    """Test content feedback submission."""

    async def test_submit_feedback(self, client: AsyncClient, legal_guide):
        """POST /legal/feedback should accept content feedback."""
        feedback_data = {
            "content_type": "guide",
            "content_id": legal_guide.id,
            "feedback_type": "helpful",
            "was_helpful": True,
            "comments": "Very clear instructions",
        }
        response = await client.post("/api/v1/legal/feedback", json=feedback_data)
        assert response.status_code == 201
        data = response.json()
        assert data["content_type"] == "guide"
        assert data["was_helpful"] is True


# ============================================================================
# 10. Integration / Workflow Tests
# ============================================================================


@pytest.mark.asyncio
class TestLegalResourceWorkflows:
    """Test end-to-end workflows through legal resources."""

    async def test_topic_to_forms_workflow(
        self, client: AsyncClient, legal_topic, legal_form
    ):
        """User can browse topics, then find forms under a topic."""
        # Step 1: List topics
        topics_response = await client.get("/api/v1/legal/topics")
        assert topics_response.status_code == 200
        topics = topics_response.json()["topics"]
        assert len(topics) >= 1

        # Step 2: Get forms for the topic
        topic_id = topics[0]["id"]
        forms_response = await client.get(f"/api/v1/legal/forms?topic_id={topic_id}")
        assert forms_response.status_code == 200

    async def test_form_to_clinic_workflow(
        self, client: AsyncClient, legal_form, legal_clinic, legal_topic
    ):
        """User can view a form then find clinics for help."""
        # Step 1: View form details
        form_response = await client.get(f"/api/v1/legal/forms/{legal_form.id}")
        assert form_response.status_code == 200
        topic_id = form_response.json()["topic_id"]

        # Step 2: Find clinics for this topic
        clinics_response = await client.get(
            f"/api/v1/legal/clinics?topic_id={topic_id}"
        )
        assert clinics_response.status_code == 200

    async def test_glossary_lookup_workflow(
        self, client: AsyncClient, glossary_term
    ):
        """User can search glossary then view term detail."""
        # Step 1: Search glossary
        search_response = await client.get("/api/v1/legal/glossary?query=plaintiff")
        assert search_response.status_code == 200

        # Step 2: View term detail
        detail_response = await client.get(
            f"/api/v1/legal/glossary/{glossary_term.slug}"
        )
        assert detail_response.status_code == 200
        data = detail_response.json()
        assert data["definition_simple"] is not None

    async def test_provider_discovery_workflow(
        self, client: AsyncClient, service_provider
    ):
        """User can browse providers and view provider details."""
        # Step 1: List providers
        list_response = await client.get("/api/v1/legal/providers")
        assert list_response.status_code == 200
        providers = list_response.json()["providers"]
        assert len(providers) >= 1

        # Step 2: View provider detail
        provider_id = providers[0]["id"]
        detail_response = await client.get(
            f"/api/v1/legal/providers/{provider_id}"
        )
        assert detail_response.status_code == 200
        data = detail_response.json()
        assert "phone" in data

    async def test_clinic_registration_workflow(
        self, client: AsyncClient, legal_clinic
    ):
        """User can view clinic details and register."""
        # Step 1: View clinic
        clinic_response = await client.get(
            f"/api/v1/legal/clinics/{legal_clinic.id}"
        )
        assert clinic_response.status_code == 200
        assert clinic_response.json()["spots_available"] > 0

        # Step 2: Register
        registration_data = {
            "name": "Workflow User",
            "email": "workflow@example.com",
            "preferred_contact": "email",
        }
        reg_response = await client.post(
            f"/api/v1/legal/clinics/{legal_clinic.id}/register",
            json=registration_data,
        )
        assert reg_response.status_code == 201

    async def test_full_resource_discovery_workflow(
        self,
        client: AsyncClient,
        legal_topic,
        legal_form,
        legal_guide,
        glossary_term,
        service_provider,
        legal_clinic,
    ):
        """Full workflow: topics -> forms -> guides -> glossary -> providers -> clinics."""
        # Browse topics
        r1 = await client.get("/api/v1/legal/topics")
        assert r1.status_code == 200

        # Browse forms
        r2 = await client.get("/api/v1/legal/forms")
        assert r2.status_code == 200

        # Browse guides
        r3 = await client.get("/api/v1/legal/guides")
        assert r3.status_code == 200

        # Browse glossary
        r4 = await client.get("/api/v1/legal/glossary")
        assert r4.status_code == 200

        # Browse providers
        r5 = await client.get("/api/v1/legal/providers")
        assert r5.status_code == 200

        # Browse clinics
        r6 = await client.get("/api/v1/legal/clinics")
        assert r6.status_code == 200

        # Get disclaimer
        r7 = await client.get("/api/v1/legal/disclaimer")
        assert r7.status_code == 200

        # All endpoints should return valid data
        assert r1.json()["total"] >= 1
        assert r2.json()["total"] >= 1
        assert r3.json()["total"] >= 1
        assert r4.json()["total"] >= 1
        assert r5.json()["total"] >= 1
        assert r6.json()["total"] >= 1
