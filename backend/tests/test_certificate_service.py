# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Unit tests for ReadingCertificateService class.

Tests certificate generation, verification, delivery, and template management
for reading program completion certificates.
"""

import pytest
from datetime import date, datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.certificate_service import ReadingCertificateService
from app.models.reading import (
    CompletionCertificate,
    CertificateTemplate,
    ReadingProgram,
    ReadingRegistration,
)
from app.models.user import User


@pytest.fixture
def mock_session():
    """Fixture for mock AsyncSession."""
    return AsyncMock(spec=AsyncSession)


@pytest.fixture
async def certificate_service(mock_session):
    """Fixture for ReadingCertificateService."""
    return ReadingCertificateService(mock_session)


@pytest.fixture
def sample_user():
    """Fixture for sample user."""
    user = User(
        id=1,
        email="test@example.com",
        first_name="Test",
        last_name="User"
    )
    return user


@pytest.fixture
def sample_program():
    """Fixture for sample reading program."""
    program = ReadingProgram(
        id=1,
        name="Summer Reading 2024",
        description="Summer reading challenge",
        start_date=date.today(),
        end_date=date.today() + timedelta(days=90),
        is_active=True,
        reading_goal_type="books",
        reading_goal_value=15
    )
    return program


@pytest.fixture
def sample_template():
    """Fixture for sample certificate template."""
    template = CertificateTemplate(
        id=1,
        name="Standard Certificate",
        description="Standard reading certificate",
        program_id=1,
        title_text="Certificate of Reading Achievement",
        congratulations_text="Congratulations!",
        recognition_text="has successfully completed the reading program",
        background_color="#FFFFFF",
        accent_color="#0066CC",
        is_active=True,
        is_default=True,
        created_by_id=1
    )
    return template


@pytest.fixture
def sample_certificate():
    """Fixture for sample completion certificate."""
    cert = CompletionCertificate(
        id=1,
        certificate_code="CERT-2024-ABC123",
        user_id=1,
        program_id=1,
        registration_id=1,
        template_id=1,
        completion_date=date.today(),
        reading_goal_achieved=20,
        reading_goal_target=15,
        issued_at=datetime.now(timezone.utc),
        is_verified=False
    )
    return cert


# ============================================================================
# Test generate_certificate
# ============================================================================

@pytest.mark.asyncio
async def test_generate_certificate_success(
    certificate_service,
    mock_session,
    sample_user,
    sample_program,
    sample_template
):
    """Test successful certificate generation."""
    # Setup
    mock_session.get.side_effect = [sample_user, sample_program]
    mock_session.flush = AsyncMock()

    with patch.object(
        certificate_service,
        '_generate_certificate_code',
        return_value="CERT-2024-ABC123"
    ):
        with patch.object(
            certificate_service,
            '_get_default_template_id',
            return_value=1
        ):
            # Execute
            cert = await certificate_service.generate_certificate(
                user_id=1,
                program_id=1,
                reading_goal_achieved=20,
                reading_goal_target=15
            )

    # Assert
    assert cert is not None
    assert cert.certificate_code == "CERT-2024-ABC123"
    assert cert.user_id == 1
    assert cert.program_id == 1
    assert cert.reading_goal_achieved == 20
    assert cert.issued_at is not None


@pytest.mark.asyncio
async def test_generate_certificate_user_not_found(certificate_service, mock_session):
    """Test certificate generation fails when user doesn't exist."""
    # Setup
    mock_session.get.return_value = None

    # Execute & Assert
    with pytest.raises(ValueError) as exc_info:
        await certificate_service.generate_certificate(
            user_id=999,
            program_id=1
        )

    assert "User" in str(exc_info.value)
    assert "not found" in str(exc_info.value)


@pytest.mark.asyncio
async def test_generate_certificate_program_not_found(
    certificate_service,
    mock_session,
    sample_user
):
    """Test certificate generation fails when program doesn't exist."""
    # Setup
    mock_session.get.side_effect = [sample_user, None]

    # Execute & Assert
    with pytest.raises(ValueError) as exc_info:
        await certificate_service.generate_certificate(
            user_id=1,
            program_id=999
        )

    assert "Reading program" in str(exc_info.value)
    assert "not found" in str(exc_info.value)


@pytest.mark.asyncio
async def test_generate_certificate_with_custom_date(
    certificate_service,
    mock_session,
    sample_user,
    sample_program
):
    """Test certificate generation with custom completion date."""
    # Setup
    mock_session.get.side_effect = [sample_user, sample_program]
    mock_session.flush = AsyncMock()

    custom_date = date(2024, 6, 15)

    with patch.object(
        certificate_service,
        '_generate_certificate_code',
        return_value="CERT-2024-ABC123"
    ):
        with patch.object(
            certificate_service,
            '_get_default_template_id',
            return_value=1
        ):
            # Execute
            cert = await certificate_service.generate_certificate(
                user_id=1,
                program_id=1,
                completion_date=custom_date
            )

    # Assert
    assert cert.completion_date == custom_date


# ============================================================================
# Test get_certificate
# ============================================================================

@pytest.mark.asyncio
async def test_get_certificate_by_code_found(
    certificate_service,
    mock_session,
    sample_certificate
):
    """Test retrieving certificate by code when it exists."""
    # Setup
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = sample_certificate
    mock_session.execute.return_value = mock_result

    # Execute
    cert = await certificate_service.get_certificate("CERT-2024-ABC123")

    # Assert
    assert cert is not None
    assert cert.certificate_code == "CERT-2024-ABC123"
    assert cert.user_id == 1


@pytest.mark.asyncio
async def test_get_certificate_by_code_not_found(certificate_service, mock_session):
    """Test retrieving certificate by code when it doesn't exist."""
    # Setup
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = mock_result

    # Execute
    cert = await certificate_service.get_certificate("CERT-2024-INVALID")

    # Assert
    assert cert is None


@pytest.mark.asyncio
async def test_get_certificate_by_id(certificate_service, mock_session, sample_certificate):
    """Test retrieving certificate by database ID."""
    # Setup
    mock_session.get.return_value = sample_certificate

    # Execute
    cert = await certificate_service.get_certificate_by_id(1)

    # Assert
    assert cert is not None
    assert cert.id == 1


# ============================================================================
# Test verify_certificate
# ============================================================================

@pytest.mark.asyncio
async def test_verify_certificate_success(
    certificate_service,
    mock_session,
    sample_certificate,
    sample_user
):
    """Test successful certificate verification."""
    # Setup
    mock_session.get.return_value = sample_user
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = sample_certificate
    mock_session.execute.return_value = mock_result
    mock_session.flush = AsyncMock()

    # Execute
    verified = await certificate_service.verify_certificate(
        certificate_code="CERT-2024-ABC123",
        verified_by_user_id=1,
        notes="Manual verification completed"
    )

    # Assert
    assert verified is not None
    assert verified.is_verified is True
    assert verified.verified_by_id == 1
    assert verified.verified_at is not None


@pytest.mark.asyncio
async def test_verify_certificate_verifier_not_found(certificate_service, mock_session):
    """Test verification fails when verifier user doesn't exist."""
    # Setup
    mock_session.get.return_value = None

    # Execute & Assert
    with pytest.raises(ValueError) as exc_info:
        await certificate_service.verify_certificate(
            certificate_code="CERT-2024-ABC123",
            verified_by_user_id=999
        )

    assert "User" in str(exc_info.value)
    assert "not found" in str(exc_info.value)


@pytest.mark.asyncio
async def test_verify_certificate_not_found(certificate_service, mock_session, sample_user):
    """Test verification when certificate doesn't exist."""
    # Setup
    mock_session.get.return_value = sample_user
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = mock_result

    # Execute
    verified = await certificate_service.verify_certificate(
        certificate_code="CERT-2024-INVALID",
        verified_by_user_id=1
    )

    # Assert
    assert verified is None


# ============================================================================
# Test email_certificate
# ============================================================================

@pytest.mark.asyncio
async def test_email_certificate_success(
    certificate_service,
    mock_session,
    sample_certificate
):
    """Test successful certificate email delivery recording."""
    # Setup
    mock_session.get.return_value = sample_certificate
    mock_session.flush = AsyncMock()

    # Execute
    updated = await certificate_service.email_certificate(
        certificate_id=1,
        email_address="recipient@example.com"
    )

    # Assert
    assert updated is not None
    assert updated.emailed_to == "recipient@example.com"
    assert updated.email_sent_at is not None


@pytest.mark.asyncio
async def test_email_certificate_not_found(certificate_service, mock_session):
    """Test email delivery when certificate doesn't exist."""
    # Setup
    mock_session.get.return_value = None

    # Execute
    updated = await certificate_service.email_certificate(
        certificate_id=999,
        email_address="test@example.com"
    )

    # Assert
    assert updated is None


# ============================================================================
# Test get_user_certificates
# ============================================================================

@pytest.mark.asyncio
async def test_get_user_certificates_success(certificate_service, mock_session):
    """Test retrieving all user certificates."""
    # Setup
    cert1 = CompletionCertificate(id=1, user_id=1, program_id=1)
    cert2 = CompletionCertificate(id=2, user_id=1, program_id=2)

    mock_result = MagicMock()
    mock_result.scalars().all.return_value = [cert1, cert2]
    mock_session.execute.return_value = mock_result

    # Execute
    certs = await certificate_service.get_user_certificates(user_id=1)

    # Assert
    assert len(certs) == 2
    assert certs[0].id == 1


@pytest.mark.asyncio
async def test_get_user_certificates_filter_by_program(certificate_service, mock_session):
    """Test retrieving user certificates for specific program."""
    # Setup
    cert = CompletionCertificate(id=1, user_id=1, program_id=1)

    mock_result = MagicMock()
    mock_result.scalars().all.return_value = [cert]
    mock_session.execute.return_value = mock_result

    # Execute
    certs = await certificate_service.get_user_certificates(
        user_id=1,
        program_id=1
    )

    # Assert
    assert len(certs) == 1
    assert certs[0].program_id == 1


@pytest.mark.asyncio
async def test_get_user_certificates_verified_only(certificate_service, mock_session):
    """Test retrieving only verified certificates."""
    # Setup
    cert = CompletionCertificate(id=1, user_id=1, is_verified=True)

    mock_result = MagicMock()
    mock_result.scalars().all.return_value = [cert]
    mock_session.execute.return_value = mock_result

    # Execute
    certs = await certificate_service.get_user_certificates(
        user_id=1,
        verified_only=True
    )

    # Assert
    assert len(certs) == 1
    assert certs[0].is_verified is True


# ============================================================================
# Test get_program_certificates
# ============================================================================

@pytest.mark.asyncio
async def test_get_program_certificates(certificate_service, mock_session):
    """Test retrieving all certificates for a program."""
    # Setup
    cert1 = CompletionCertificate(id=1, user_id=1, program_id=1)
    cert2 = CompletionCertificate(id=2, user_id=2, program_id=1)
    cert3 = CompletionCertificate(id=3, user_id=3, program_id=1)

    mock_result = MagicMock()
    mock_result.scalars().all.return_value = [cert1, cert2, cert3]
    mock_session.execute.return_value = mock_result

    # Execute
    certs = await certificate_service.get_program_certificates(program_id=1)

    # Assert
    assert len(certs) == 3
    assert all(c.program_id == 1 for c in certs)


@pytest.mark.asyncio
async def test_get_program_certificates_verified_only(certificate_service, mock_session):
    """Test retrieving verified certificates for a program."""
    # Setup
    cert_verified = CompletionCertificate(id=1, program_id=1, is_verified=True)
    _ = CompletionCertificate(id=2, program_id=1, is_verified=False)

    mock_result = MagicMock()
    mock_result.scalars().all.return_value = [cert_verified]
    mock_session.execute.return_value = mock_result

    # Execute
    certs = await certificate_service.get_program_certificates(
        program_id=1,
        verified_only=True
    )

    # Assert
    assert len(certs) == 1
    assert certs[0].is_verified is True


# ============================================================================
# Test get_template
# ============================================================================

@pytest.mark.asyncio
async def test_get_template_by_id(certificate_service, mock_session, sample_template):
    """Test retrieving template by ID."""
    # Setup
    mock_session.get.return_value = sample_template

    # Execute
    template = await certificate_service.get_template(template_id=1)

    # Assert
    assert template is not None
    assert template.id == 1


@pytest.mark.asyncio
async def test_get_template_by_program_id(certificate_service, mock_session, sample_template):
    """Test retrieving template for specific program."""
    # Setup
    mock_result = MagicMock()
    mock_result.scalars().first.return_value = sample_template
    mock_session.execute.return_value = mock_result

    # Execute
    template = await certificate_service.get_template(program_id=1)

    # Assert
    assert template is not None
    assert template.program_id == 1


@pytest.mark.asyncio
async def test_get_template_fallback_to_default(certificate_service, mock_session):
    """Test fallback to organization default template."""
    # Setup
    default_template = CertificateTemplate(
        id=99,
        name="Default Template",
        program_id=None,  # Organization-wide default
        is_default=True,
        is_active=True
    )

    mock_result = MagicMock()
    mock_result.scalars().first.return_value = default_template
    mock_session.execute.return_value = mock_result

    # Execute
    template = await certificate_service.get_template(program_id=999)

    # Assert
    assert template is not None
    assert template.is_default is True


# ============================================================================
# Test create_template
# ============================================================================

@pytest.mark.asyncio
async def test_create_template_success(certificate_service, mock_session):
    """Test successful template creation."""
    # Setup
    mock_session.add = MagicMock()
    mock_session.flush = AsyncMock()

    # Execute
    template = await certificate_service.create_template(
        name="Custom Template",
        title_text="Custom Certificate",
        congratulations_text="Well done!",
        recognition_text="You have completed",
        program_id=1,
        background_color="#F0F0F0",
        accent_color="#FF6600",
        created_by_id=1
    )

    # Assert
    assert template is not None
    assert template.name == "Custom Template"
    assert template.program_id == 1
    assert template.background_color == "#F0F0F0"
    assert template.is_active is True


@pytest.mark.asyncio
async def test_create_template_as_default(certificate_service, mock_session):
    """Test creating template as default."""
    # Setup
    mock_session.add = MagicMock()
    mock_session.flush = AsyncMock()

    # Execute
    template = await certificate_service.create_template(
        name="Default Template",
        title_text="Certificate",
        congratulations_text="Congratulations",
        recognition_text="has completed",
        is_default=True
    )

    # Assert
    assert template.is_default is True


# ============================================================================
# Test get_program_templates
# ============================================================================

@pytest.mark.asyncio
async def test_get_program_templates(certificate_service, mock_session, sample_template):
    """Test retrieving all templates for a program."""
    # Setup
    mock_result = MagicMock()
    mock_result.scalars().all.return_value = [sample_template]
    mock_session.execute.return_value = mock_result

    # Execute
    templates = await certificate_service.get_program_templates(program_id=1)

    # Assert
    assert len(templates) == 1
    assert templates[0].program_id == 1


@pytest.mark.asyncio
async def test_get_program_templates_include_inactive(certificate_service, mock_session):
    """Test retrieving all templates including inactive ones."""
    # Setup
    active = CertificateTemplate(id=1, program_id=1, is_active=True)
    inactive = CertificateTemplate(id=2, program_id=1, is_active=False)

    mock_result = MagicMock()
    mock_result.scalars().all.return_value = [active, inactive]
    mock_session.execute.return_value = mock_result

    # Execute
    templates = await certificate_service.get_program_templates(
        program_id=1,
        include_inactive=True
    )

    # Assert
    assert len(templates) == 2


# ============================================================================
# Test Certificate Code Generation
# ============================================================================

async def test_generate_certificate_code_format():
    """Test certificate code format."""
    service = ReadingCertificateService(AsyncMock(spec=AsyncSession))
    code = service._generate_certificate_code()

    # Assert
    assert code.startswith("CERT-")
    assert len(code) > 10  # CERT-YYYY-XXXXXX format
    parts = code.split("-")
    assert len(parts) == 3
    assert parts[0] == "CERT"
    assert parts[1].isdigit()  # Year
    assert len(parts[2]) == 6  # 6-char hex


async def test_generate_certificate_code_uniqueness():
    """Test that generated codes are unique."""
    service = ReadingCertificateService(AsyncMock(spec=AsyncSession))
    codes = {service._generate_certificate_code() for _ in range(100)}

    # Assert - all codes should be unique
    assert len(codes) == 100


# ============================================================================
# Test update_certificate_pdf_url
# ============================================================================

@pytest.mark.asyncio
async def test_update_certificate_pdf_url(
    certificate_service,
    mock_session,
    sample_certificate
):
    """Test updating certificate PDF URL."""
    # Setup
    mock_session.get.return_value = sample_certificate
    mock_session.flush = AsyncMock()

    # Execute
    updated = await certificate_service.update_certificate_pdf_url(
        certificate_id=1,
        pdf_url="https://example.com/certs/CERT-2024-ABC123.pdf"
    )

    # Assert
    assert updated is not None
    assert updated.certificate_pdf_url == "https://example.com/certs/CERT-2024-ABC123.pdf"


# ============================================================================
# Test update_certificate_badge_url
# ============================================================================

@pytest.mark.asyncio
async def test_update_certificate_badge_url(
    certificate_service,
    mock_session,
    sample_certificate
):
    """Test updating certificate digital badge URL."""
    # Setup
    mock_session.get.return_value = sample_certificate
    mock_session.flush = AsyncMock()

    # Execute
    updated = await certificate_service.update_certificate_badge_url(
        certificate_id=1,
        badge_url="https://example.com/badges/badge-abc123.png"
    )

    # Assert
    assert updated is not None
    assert updated.digital_badge_url == "https://example.com/badges/badge-abc123.png"


# ============================================================================
# Test _get_default_template_id
# ============================================================================

@pytest.mark.asyncio
async def test_get_default_template_id(certificate_service, mock_session, sample_template):
    """Test getting default template ID for a program."""
    # Setup
    with patch.object(
        certificate_service,
        'get_template',
        return_value=sample_template
    ):
        # Execute
        template_id = await certificate_service._get_default_template_id(1)

    # Assert
    assert template_id == 1


@pytest.mark.asyncio
async def test_get_default_template_id_not_found(certificate_service, mock_session):
    """Test getting default template ID when no template exists."""
    # Setup
    with patch.object(
        certificate_service,
        'get_template',
        return_value=None
    ):
        # Execute
        template_id = await certificate_service._get_default_template_id(1)

    # Assert
    assert template_id is None
