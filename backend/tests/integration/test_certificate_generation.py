# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Integration tests for certificate generation and validation.

Tests cover:
- Certificate generation upon course completion
- Unique certificate ID generation (format: L30-XXXXXXXX)
- Certificate verification endpoints (public access)
- PDF download functionality
- Duplicate certificate prevention
- Certificate listing for users
"""

import re
import uuid
from io import BytesIO

import pytest


def _error_detail(response) -> str:
    """Error responses are wrapped as {"error": {"message": ...}} by
    app.core.exception_handlers.http_exception_handler, not the FastAPI
    default {"detail": ...}."""
    data = response.json()
    if "detail" in data:
        return str(data["detail"])
    return str(data.get("error", {}).get("message", data))


@pytest.fixture
async def test_user(test_db):
    """Create a test user for certificate tests."""
    from app.core.security import hash_password
    from app.models.user import User, UserRole

    user = User(
        email="certuser@example.com",
        password_hash=hash_password("CertPassword123!"),
        first_name="Certificate",
        last_name="Tester",
        role=UserRole.PATRON,
        is_active=True,
        email_verified=True,
    )
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)
    return user


@pytest.fixture
async def test_course(test_db):
    """Create a published test course with a module and lesson."""
    from app.models.learning import Course, CourseLifecycleStage, Lesson, Module

    course = Course(
        title="Certificate Test Course",
        description="A course for testing certificate generation",
        access_level="patron",
        lifecycle_stage=CourseLifecycleStage.PUBLISHED,
        difficulty="beginner",
        estimated_minutes=30,
        quiz_passing_threshold=70,
        xp_reward=100,
    )
    test_db.add(course)
    await test_db.commit()
    await test_db.refresh(course)

    # Add a module
    module = Module(
        course_id=course.id,
        title="Test Module",
        description="Module for testing",
        sort_order=0,
    )
    test_db.add(module)
    await test_db.commit()
    await test_db.refresh(module)

    # Add a lesson to the module
    lesson = Lesson(
        module_id=module.id,
        title="Test Lesson",
        lesson_type="article",
        content={"text": "Lesson content for certificate testing"},
        estimated_minutes=15,
        sort_order=0,
    )
    test_db.add(lesson)
    await test_db.commit()
    await test_db.refresh(lesson)

    return course


@pytest.fixture
async def enrolled_user_with_progress(test_db, test_user, test_course):
    """Create user with enrollment and completed lesson progress."""
    from sqlalchemy import select

    from app.models.learning import Enrollment, Lesson, LessonProgress, Module

    # Enroll user in course
    enrollment = Enrollment(
        user_id=test_user.id,
        course_id=test_course.id,
    )
    test_db.add(enrollment)
    await test_db.commit()

    # Get the lesson(s) for the course
    result = await test_db.execute(
        select(Lesson).join(Module).where(Module.course_id == test_course.id)
    )
    lessons = result.scalars().all()

    # Mark all lessons as completed
    for lesson in lessons:
        progress = LessonProgress(
            user_id=test_user.id,
            lesson_id=lesson.id,
            status="completed",
        )
        test_db.add(progress)

    await test_db.commit()
    return test_user


async def get_user_token(client, email, password):
    """Helper to get user authentication token."""
    login_data = {
        "username": email,
        "password": password,
    }
    response = await client.post("/api/v1/auth/login", json=login_data)
    if response.status_code != 200:
        raise Exception(f"Login failed: {response.json()}")
    return response.json()["access_token"]


# ============ CERTIFICATE GENERATION TESTS ============


@pytest.mark.integration
class TestCertificateGeneration:
    """Tests for certificate generation when course is completed."""

    async def test_generate_certificate_on_course_completion(
        self, client, enrolled_user_with_progress, test_course
    ):
        """Test that certificate is generated when all lessons are completed."""
        token = await get_user_token(client, "certuser@example.com", "CertPassword123!")

        response = await client.post(
            f"/api/v1/learning/courses/{test_course.id}/certificate",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()

        # Verify certificate data
        assert data["course_id"] == test_course.id
        assert data["course_title"] == test_course.title
        assert "certificate_number" in data
        assert "issued_at" in data

    async def test_certificate_number_format(
        self, client, enrolled_user_with_progress, test_course
    ):
        """Test that certificate number follows format L30-XXXXXXXX."""
        token = await get_user_token(client, "certuser@example.com", "CertPassword123!")

        response = await client.post(
            f"/api/v1/learning/courses/{test_course.id}/certificate",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        cert_number = response.json()["certificate_number"]

        # Verify format: L30- followed by 8 uppercase hex characters
        pattern = r"^L30-[A-F0-9]{8}$"
        assert re.match(pattern, cert_number), (
            f"Certificate number {cert_number} doesn't match expected format"
        )

    async def test_cannot_generate_duplicate_certificate(
        self, client, enrolled_user_with_progress, test_course
    ):
        """Test that duplicate certificates cannot be generated."""
        token = await get_user_token(client, "certuser@example.com", "CertPassword123!")

        # First certificate generation
        response1 = await client.post(
            f"/api/v1/learning/courses/{test_course.id}/certificate",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response1.status_code == 200

        # Second attempt should fail
        response2 = await client.post(
            f"/api/v1/learning/courses/{test_course.id}/certificate",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response2.status_code == 400
        assert "already issued" in _error_detail(response2).lower()

    async def test_cannot_generate_certificate_without_enrollment(
        self, client, test_user, test_course
    ):
        """Test that certificate cannot be generated without enrollment."""
        token = await get_user_token(client, "certuser@example.com", "CertPassword123!")

        response = await client.post(
            f"/api/v1/learning/courses/{test_course.id}/certificate",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 404
        assert "not enrolled" in _error_detail(response).lower()

    async def test_cannot_generate_certificate_without_completion(
        self, client, test_db, test_user, test_course
    ):
        """Test that certificate cannot be generated without completing lessons."""
        from app.models.learning import Enrollment

        # Enroll user but don't complete lessons
        enrollment = Enrollment(
            user_id=test_user.id,
            course_id=test_course.id,
        )
        test_db.add(enrollment)
        await test_db.commit()

        token = await get_user_token(client, "certuser@example.com", "CertPassword123!")

        response = await client.post(
            f"/api/v1/learning/courses/{test_course.id}/certificate",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 400
        assert "complete all lessons" in _error_detail(response).lower()

    async def test_certificate_requires_authentication(self, client, test_course):
        """Test that certificate generation requires authentication."""
        response = await client.post(
            f"/api/v1/learning/courses/{test_course.id}/certificate",
        )
        assert response.status_code == 401


# ============ UNIQUE CERTIFICATE ID TESTS ============


@pytest.mark.integration
class TestUniqueCertificateIds:
    """Tests for unique certificate ID generation."""

    async def test_certificate_ids_are_unique(self, test_db):
        """Test that generated certificate IDs are unique."""
        # Generate multiple certificate IDs
        generated_ids = set()
        for _ in range(100):
            cert_id = f"L30-{uuid.uuid4().hex[:8].upper()}"
            generated_ids.add(cert_id)

        # All IDs should be unique (100 unique IDs)
        assert len(generated_ids) == 100

    async def test_certificate_number_stored_correctly(
        self, client, test_db, enrolled_user_with_progress, test_course
    ):
        """Test that certificate number is correctly stored in database."""
        from sqlalchemy import select

        from app.models.learning import Certificate

        token = await get_user_token(client, "certuser@example.com", "CertPassword123!")

        response = await client.post(
            f"/api/v1/learning/courses/{test_course.id}/certificate",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200

        cert_number = response.json()["certificate_number"]

        # Verify in database
        result = await test_db.execute(
            select(Certificate).where(Certificate.certificate_number == cert_number)
        )
        db_cert = result.scalar_one_or_none()
        assert db_cert is not None
        assert db_cert.certificate_number == cert_number


# ============ CERTIFICATE VERIFICATION TESTS ============


@pytest.mark.integration
class TestCertificateVerification:
    """Tests for certificate verification endpoints."""

    async def test_verify_valid_certificate(self, client, enrolled_user_with_progress, test_course):
        """Test verifying a valid certificate."""
        token = await get_user_token(client, "certuser@example.com", "CertPassword123!")

        # Generate certificate
        gen_response = await client.post(
            f"/api/v1/learning/courses/{test_course.id}/certificate",
            headers={"Authorization": f"Bearer {token}"},
        )
        cert_number = gen_response.json()["certificate_number"]

        # Verify certificate (public endpoint - no auth required)
        verify_response = await client.get(
            f"/api/v1/learning/certificates/{cert_number}/verify",
        )
        assert verify_response.status_code == 200
        data = verify_response.json()

        assert data["certificate_number"] == cert_number
        assert data["is_valid"] is True
        assert data["user_name"] == "Certificate Tester"
        assert data["course_title"] == test_course.title
        assert "issued_at" in data

    async def test_verify_invalid_certificate(self, client):
        """Test verifying an invalid certificate number."""
        response = await client.get(
            "/api/v1/learning/certificates/L30-INVALID1/verify",
        )
        assert response.status_code == 404
        assert "not found" in _error_detail(response).lower()

    async def test_verification_is_public(self, client, enrolled_user_with_progress, test_course):
        """Test that verification endpoint is publicly accessible."""
        token = await get_user_token(client, "certuser@example.com", "CertPassword123!")

        # Generate certificate
        gen_response = await client.post(
            f"/api/v1/learning/courses/{test_course.id}/certificate",
            headers={"Authorization": f"Bearer {token}"},
        )
        cert_number = gen_response.json()["certificate_number"]

        # Verify without authentication
        response = await client.get(
            f"/api/v1/learning/certificates/{cert_number}/verify",
        )
        assert response.status_code == 200


# ============ CERTIFICATE LISTING TESTS ============


@pytest.mark.integration
class TestCertificateListing:
    """Tests for listing user certificates."""

    async def test_list_user_certificates(self, client, enrolled_user_with_progress, test_course):
        """Test listing certificates for authenticated user."""
        token = await get_user_token(client, "certuser@example.com", "CertPassword123!")

        # Generate certificate first
        await client.post(
            f"/api/v1/learning/courses/{test_course.id}/certificate",
            headers={"Authorization": f"Bearer {token}"},
        )

        # List certificates
        response = await client.get(
            "/api/v1/learning/certificates",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        certificates = response.json()

        assert len(certificates) >= 1
        assert any(c["course_id"] == test_course.id for c in certificates)

    async def test_list_certificates_requires_auth(self, client):
        """Test that listing certificates requires authentication."""
        response = await client.get("/api/v1/learning/certificates")
        assert response.status_code == 401

    async def test_user_only_sees_own_certificates(
        self, client, test_db, enrolled_user_with_progress, test_course
    ):
        """Test that users only see their own certificates."""
        from app.core.security import hash_password
        from app.models.user import User, UserRole

        # Generate certificate for first user
        token1 = await get_user_token(client, "certuser@example.com", "CertPassword123!")
        await client.post(
            f"/api/v1/learning/courses/{test_course.id}/certificate",
            headers={"Authorization": f"Bearer {token1}"},
        )

        # Create second user
        user2 = User(
            email="certuser2@example.com",
            password_hash=hash_password("CertPassword123!"),
            first_name="Another",
            last_name="User",
            role=UserRole.PATRON,
            is_active=True,
            email_verified=True,
        )
        test_db.add(user2)
        await test_db.commit()

        # Second user's certificate list should be empty
        token2 = await get_user_token(client, "certuser2@example.com", "CertPassword123!")
        response = await client.get(
            "/api/v1/learning/certificates",
            headers={"Authorization": f"Bearer {token2}"},
        )
        assert response.status_code == 200
        assert len(response.json()) == 0


# ============ PDF DOWNLOAD TESTS ============


@pytest.mark.integration
class TestCertificatePdfDownload:
    """Tests for certificate PDF download functionality."""

    async def test_download_certificate_pdf(self, client, enrolled_user_with_progress, test_course):
        """Test downloading certificate as PDF."""
        token = await get_user_token(client, "certuser@example.com", "CertPassword123!")

        # Generate certificate first
        await client.post(
            f"/api/v1/learning/courses/{test_course.id}/certificate",
            headers={"Authorization": f"Bearer {token}"},
        )

        # Download PDF
        response = await client.get(
            f"/api/v1/learning/certificates/{test_course.id}/download",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/pdf"
        assert "attachment" in response.headers.get("content-disposition", "")

        # Verify PDF content starts with PDF header
        assert response.content[:4] == b"%PDF"

    async def test_download_pdf_requires_auth(self, client, test_course):
        """Test that PDF download requires authentication."""
        response = await client.get(
            f"/api/v1/learning/certificates/{test_course.id}/download",
        )
        assert response.status_code == 401

    async def test_download_pdf_not_found_without_certificate(self, client, test_user, test_course):
        """Test that PDF download fails without certificate."""
        token = await get_user_token(client, "certuser@example.com", "CertPassword123!")

        response = await client.get(
            f"/api/v1/learning/certificates/{test_course.id}/download",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 404

    async def test_pdf_contains_verification_url(
        self, client, enrolled_user_with_progress, test_course
    ):
        """Test that PDF contains verification URL."""
        token = await get_user_token(client, "certuser@example.com", "CertPassword123!")

        # Generate certificate
        gen_response = await client.post(
            f"/api/v1/learning/courses/{test_course.id}/certificate",
            headers={"Authorization": f"Bearer {token}"},
        )
        cert_number = gen_response.json()["certificate_number"]

        # Download PDF
        response = await client.get(
            f"/api/v1/learning/certificates/{test_course.id}/download",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200

        # The certificate number should be present in the PDF's text content.
        # reportlab's Canvas compresses content streams by default, so the
        # cert number won't appear as literal bytes in the raw PDF -- extract
        # text properly instead of grepping the compressed bytes.
        from pypdf import PdfReader

        pdf_content = response.content
        reader = PdfReader(BytesIO(pdf_content))
        text = "\n".join(page.extract_text() for page in reader.pages)
        assert cert_number in text or "verify" in text.lower()


# ============ DATABASE CONSTRAINT TESTS ============


@pytest.mark.integration
class TestCertificateDatabaseConstraints:
    """Tests for certificate database constraints."""

    async def test_unique_constraint_user_course(
        self, test_db, enrolled_user_with_progress, test_course
    ):
        """Test unique constraint on user_id and course_id combination."""
        from sqlalchemy.exc import IntegrityError

        from app.models.learning import Certificate

        # Create first certificate
        cert1 = Certificate(
            user_id=enrolled_user_with_progress.id,
            course_id=test_course.id,
            certificate_number=f"L30-{uuid.uuid4().hex[:8].upper()}",
        )
        test_db.add(cert1)
        await test_db.commit()

        # Attempt to create duplicate should fail
        cert2 = Certificate(
            user_id=enrolled_user_with_progress.id,
            course_id=test_course.id,
            certificate_number=f"L30-{uuid.uuid4().hex[:8].upper()}",
        )
        test_db.add(cert2)

        with pytest.raises(IntegrityError):
            await test_db.commit()

    async def test_unique_constraint_certificate_number(self, test_db, test_user, test_course):
        """Test unique constraint on certificate_number."""
        from sqlalchemy.exc import IntegrityError

        from app.models.learning import Certificate, Course, CourseLifecycleStage

        # Create another course
        course2 = Course(
            title="Another Course",
            description="Second course",
            lifecycle_stage=CourseLifecycleStage.PUBLISHED,
            access_level="patron",
        )
        test_db.add(course2)
        await test_db.commit()
        await test_db.refresh(course2)

        cert_number = f"L30-{uuid.uuid4().hex[:8].upper()}"

        # Create first certificate
        cert1 = Certificate(
            user_id=test_user.id,
            course_id=test_course.id,
            certificate_number=cert_number,
        )
        test_db.add(cert1)
        await test_db.commit()

        # Attempt to reuse certificate number should fail
        cert2 = Certificate(
            user_id=test_user.id,
            course_id=course2.id,
            certificate_number=cert_number,  # Same certificate number
        )
        test_db.add(cert2)

        with pytest.raises(IntegrityError):
            await test_db.commit()
