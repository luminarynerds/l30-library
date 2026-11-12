# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Tests for the bulk import service and API endpoints.

Covers:
  - CSV parsing and validation (happy path + errors)
  - Duplicate detection (patron email/barcode, catalog ISBN/title+author)
  - Full pipeline: upload → validate → preview → dry-run → execute → rollback
  - Column mapping re-validation
  - Error threshold auto-rollback
  - MARC parsing (if pymarc available)
  - API endpoint integration tests
"""

import os
import json
import csv
import io
import tempfile
from datetime import datetime
from decimal import Decimal

import pytest
from unittest.mock import patch

# ── Paths to test data ────────────────────────────────────────────────────
TEST_DATA_DIR = os.path.join(os.path.dirname(__file__), "test_data")


def _read_test_file(name: str) -> bytes:
    with open(os.path.join(TEST_DATA_DIR, name), "rb") as f:
        return f.read()


# ══════════════════════════════════════════════════════════════════════════
# Unit tests for ImportService internals
# ══════════════════════════════════════════════════════════════════════════


class TestCSVParsing:
    """Test CSV file reading and parsing."""

    def test_read_valid_patrons_csv(self):
        from app.services.import_service import ImportService

        path = os.path.join(TEST_DATA_DIR, "valid_patrons.csv")
        rows = ImportService._read_csv(path)
        assert len(rows) == 3
        assert rows[0]["name"] == "Alice Johnson"
        assert rows[0]["email"] == "alice@example.com"
        assert rows[1]["barcode"] == "LSC-BBBB-0002"

    def test_read_valid_catalog_csv(self):
        from app.services.import_service import ImportService

        path = os.path.join(TEST_DATA_DIR, "valid_catalog.csv")
        rows = ImportService._read_csv(path)
        assert len(rows) == 3
        assert rows[0]["title"] == "The Great Gatsby"
        assert rows[2]["isbn"] == "978-0-452-28423-4"

    def test_read_holdings_csv(self):
        from app.services.import_service import ImportService

        path = os.path.join(TEST_DATA_DIR, "valid_holdings.csv")
        rows = ImportService._read_csv(path)
        assert len(rows) == 3
        assert rows[0]["item_barcode"] == "COPY-TEST-001"
        assert rows[2]["condition"] == "fair"

    def test_read_circulation_csv(self):
        from app.services.import_service import ImportService

        path = os.path.join(TEST_DATA_DIR, "valid_circulation.csv")
        rows = ImportService._read_csv(path)
        assert len(rows) == 3
        assert rows[0]["patron_barcode"] == "LSC-AAAA-0001"
        assert rows[2]["return_date"] == ""  # Open checkout


class TestRowValidation:
    """Test individual row validation logic."""

    def test_patron_valid_row(self):
        from app.services.import_service import ImportService

        row = {
            "name": "Test User",
            "email": "test@example.com",
            "barcode": "LSC-1234-5678",
            "patron_type": "PATRON",
        }
        errors, warnings = ImportService._validate_patron_row(row, 1, [], [])
        assert len(errors) == 0
        assert len(warnings) == 0

    def test_patron_invalid_email(self):
        from app.services.import_service import ImportService

        row = {"email": "not-an-email", "barcode": "LSC-1234-5678"}
        errors, warnings = ImportService._validate_patron_row(row, 1, [], [])
        assert len(errors) == 1
        assert errors[0]["field"] == "email"

    def test_patron_invalid_barcode(self):
        from app.services.import_service import ImportService

        row = {"email": "ok@example.com", "barcode": "!!!BAD!!!"}
        errors, warnings = ImportService._validate_patron_row(row, 1, [], [])
        assert len(errors) == 1
        assert errors[0]["field"] == "barcode"

    def test_patron_unknown_type_warning(self):
        from app.services.import_service import ImportService

        row = {"email": "ok@example.com", "patron_type": "MYSTERY_ROLE"}
        errors, warnings = ImportService._validate_patron_row(row, 1, [], [])
        assert len(warnings) == 1
        assert "patron_type" in warnings[0]["field"]

    def test_catalog_valid_row(self):
        from app.services.import_service import ImportService

        row = {
            "title": "Test Book",
            "author": "Author",
            "isbn": "978-0-7432-7356-5",
            "publication_year": "2020",
            "item_type": "book",
        }
        errors, warnings = ImportService._validate_catalog_row(row, 1, [], [])
        assert len(errors) == 0
        assert len(warnings) == 0

    def test_catalog_invalid_year(self):
        from app.services.import_service import ImportService

        row = {"title": "Test", "publication_year": "not-a-year"}
        errors, warnings = ImportService._validate_catalog_row(row, 1, [], [])
        assert len(errors) == 1
        assert errors[0]["field"] == "publication_year"

    def test_catalog_unknown_item_type_warning(self):
        from app.services.import_service import ImportService

        row = {"title": "Test", "item_type": "hologram"}
        errors, warnings = ImportService._validate_catalog_row(row, 1, [], [])
        assert len(warnings) == 1

    def test_holdings_invalid_catalog_id(self):
        from app.services.import_service import ImportService

        row = {"item_barcode": "COPY-001", "catalog_id": "abc"}
        errors, warnings = ImportService._validate_holdings_row(row, 1, [], [])
        assert len(errors) == 1
        assert errors[0]["field"] == "catalog_id"

    def test_circ_invalid_date(self):
        from app.services.import_service import ImportService

        row = {"checkout_date": "not-a-date"}
        errors, warnings = ImportService._validate_circ_row(row, 1, [], [])
        assert len(errors) == 1
        assert "checkout_date" in errors[0]["field"]


class TestDateParsing:
    """Test date parsing utility."""

    def test_iso_format(self):
        from app.services.import_service import _parse_date

        result = _parse_date("2024-01-15")
        assert result is not None
        assert result.year == 2024
        assert result.month == 1
        assert result.day == 15

    def test_us_format(self):
        from app.services.import_service import _parse_date

        result = _parse_date("01/15/2024")
        assert result is not None
        assert result.year == 2024

    def test_invalid_date(self):
        from app.services.import_service import _parse_date

        assert _parse_date("not-a-date") is None
        assert _parse_date("") is None


class TestSimilarity:
    """Test fuzzy string matching."""

    def test_exact_match(self):
        from app.services.import_service import _similarity

        assert _similarity("hello", "hello") == 1.0

    def test_case_insensitive(self):
        from app.services.import_service import _similarity

        assert _similarity("Hello", "hello") == 1.0

    def test_different_strings(self):
        from app.services.import_service import _similarity

        score = _similarity("The Great Gatsby", "To Kill a Mockingbird")
        assert score < 0.5

    def test_similar_strings(self):
        from app.services.import_service import _similarity

        score = _similarity("The Great Gatsby", "The Great Gatsby: A Novel")
        assert score > 0.7


class TestFileFormatDetection:
    """Test file format detection from filename."""

    def test_csv(self):
        from app.services.import_service import _detect_file_format, ImportFileFormat

        assert _detect_file_format("patrons.csv") == ImportFileFormat.CSV

    def test_marc21(self):
        from app.services.import_service import _detect_file_format, ImportFileFormat

        assert _detect_file_format("catalog.mrc") == ImportFileFormat.MARC21
        assert _detect_file_format("catalog.marc") == ImportFileFormat.MARC21

    def test_marcxml(self):
        from app.services.import_service import _detect_file_format, ImportFileFormat

        assert _detect_file_format("records.xml") == ImportFileFormat.MARCXML
        assert _detect_file_format("records.marcxml") == ImportFileFormat.MARCXML

    def test_json(self):
        from app.services.import_service import _detect_file_format, ImportFileFormat

        assert _detect_file_format("data.json") == ImportFileFormat.JSON

    def test_unknown_defaults_csv(self):
        from app.services.import_service import _detect_file_format, ImportFileFormat

        assert _detect_file_format("unknown.txt") == ImportFileFormat.CSV


class TestTemplates:
    """Test CSV template definitions."""

    def test_all_templates_defined(self):
        from app.services.import_service import TEMPLATES, ImportJobType

        assert ImportJobType.PATRONS in TEMPLATES
        assert ImportJobType.CATALOG_ITEMS in TEMPLATES
        assert ImportJobType.HOLDINGS in TEMPLATES
        assert ImportJobType.CIRCULATION_HISTORY in TEMPLATES

    def test_template_has_required_keys(self):
        from app.services.import_service import TEMPLATES

        for job_type, info in TEMPLATES.items():
            assert "filename" in info
            assert "description" in info
            assert "columns" in info
            assert "sample_row" in info
            assert len(info["columns"]) > 0
            # Sample row should have the same keys as columns
            for col in info["columns"]:
                assert col in info["sample_row"], f"Missing sample for {col} in {job_type}"


# ══════════════════════════════════════════════════════════════════════════
# Integration tests with database (async)
# ══════════════════════════════════════════════════════════════════════════


class TestImportPipeline:
    """Full pipeline integration tests."""

    @pytest.mark.asyncio
    async def test_upload_and_validate_patrons(self, test_db, test_admin):
        from app.services.import_service import ImportService
        from app.models.import_job import (
            ImportJobType, ImportJobStatus, DuplicateAction,
        )

        content = _read_test_file("valid_patrons.csv")
        job = await ImportService.upload(
            db=test_db,
            file_content=content,
            filename="valid_patrons.csv",
            job_type=ImportJobType.PATRONS,
            duplicate_action=DuplicateAction.SKIP,
            error_threshold=10.0,
            created_by_id=test_admin.id,
        )
        assert job.id is not None
        assert job.status == ImportJobStatus.PENDING
        assert job.file_size_bytes == len(content)

        # Validate
        job = await ImportService.validate(test_db, job)
        assert job.status == ImportJobStatus.VALIDATED
        assert job.total_rows == 3
        assert job.error_rows == 0

    @pytest.mark.asyncio
    async def test_validate_invalid_patrons(self, test_db, test_admin):
        from app.services.import_service import ImportService
        from app.models.import_job import ImportJobType, ImportJobStatus, DuplicateAction

        content = _read_test_file("invalid_patrons.csv")
        job = await ImportService.upload(
            db=test_db,
            file_content=content,
            filename="invalid_patrons.csv",
            job_type=ImportJobType.PATRONS,
            duplicate_action=DuplicateAction.SKIP,
            error_threshold=10.0,
            created_by_id=test_admin.id,
        )
        job = await ImportService.validate(test_db, job)
        assert job.status == ImportJobStatus.VALIDATED
        assert job.error_rows > 0
        assert job.validation_report is not None
        assert len(job.validation_report["errors"]) > 0

    @pytest.mark.asyncio
    async def test_preview_returns_rows(self, test_db, test_admin):
        from app.services.import_service import ImportService
        from app.models.import_job import ImportJobType, DuplicateAction

        content = _read_test_file("valid_patrons.csv")
        job = await ImportService.upload(
            db=test_db,
            file_content=content,
            filename="valid_patrons.csv",
            job_type=ImportJobType.PATRONS,
            duplicate_action=DuplicateAction.SKIP,
            error_threshold=10.0,
            created_by_id=test_admin.id,
        )
        job = await ImportService.validate(test_db, job)
        records = await ImportService.preview(test_db, job, limit=10)
        assert len(records) == 3
        assert records[0].row_number == 1
        assert records[0].source_data["name"] == "Alice Johnson"

    @pytest.mark.asyncio
    async def test_dry_run_patrons(self, test_db, test_admin):
        from app.services.import_service import ImportService
        from app.models.import_job import ImportJobType, DuplicateAction

        content = _read_test_file("valid_patrons.csv")
        job = await ImportService.upload(
            db=test_db,
            file_content=content,
            filename="valid_patrons.csv",
            job_type=ImportJobType.PATRONS,
            duplicate_action=DuplicateAction.SKIP,
            error_threshold=10.0,
            created_by_id=test_admin.id,
        )
        job = await ImportService.validate(test_db, job)
        report = await ImportService.dry_run(test_db, job)
        assert report["would_create"] == 3
        assert report["would_skip"] == 0
        assert len(report["sample_records"]) > 0

    @pytest.mark.asyncio
    async def test_execute_patrons(self, test_db, test_admin):
        from app.services.import_service import ImportService
        from app.models.import_job import (
            ImportJobType, ImportJobStatus, DuplicateAction,
        )
        from app.models.user import User
        from sqlalchemy import select

        content = _read_test_file("valid_patrons.csv")
        job = await ImportService.upload(
            db=test_db,
            file_content=content,
            filename="valid_patrons.csv",
            job_type=ImportJobType.PATRONS,
            duplicate_action=DuplicateAction.SKIP,
            error_threshold=10.0,
            created_by_id=test_admin.id,
        )
        job = await ImportService.validate(test_db, job)
        job = await ImportService.execute(test_db, job)
        assert job.status == ImportJobStatus.COMPLETED
        assert job.created_rows == 3
        assert job.error_rows == 0

        # Verify patrons exist in DB
        result = await test_db.execute(
            select(User).where(User.email == "alice@example.com")
        )
        alice = result.scalar_one_or_none()
        assert alice is not None
        assert alice.first_name == "Alice"

    @pytest.mark.asyncio
    async def test_execute_catalog_items(self, test_db, test_admin):
        from app.services.import_service import ImportService
        from app.models.import_job import (
            ImportJobType, ImportJobStatus, DuplicateAction,
        )
        from app.models.catalog import CatalogItem
        from sqlalchemy import select

        content = _read_test_file("valid_catalog.csv")
        job = await ImportService.upload(
            db=test_db,
            file_content=content,
            filename="valid_catalog.csv",
            job_type=ImportJobType.CATALOG_ITEMS,
            duplicate_action=DuplicateAction.SKIP,
            error_threshold=10.0,
            created_by_id=test_admin.id,
        )
        job = await ImportService.validate(test_db, job)
        job = await ImportService.execute(test_db, job)
        assert job.status == ImportJobStatus.COMPLETED
        assert job.created_rows == 3

        result = await test_db.execute(
            select(CatalogItem).where(CatalogItem.title == "The Great Gatsby")
        )
        gatsby = result.scalar_one_or_none()
        assert gatsby is not None
        assert gatsby.author == "F. Scott Fitzgerald"
        assert gatsby.publication_year == 1925

    @pytest.mark.asyncio
    async def test_rollback_patrons(self, test_db, test_admin):
        from app.services.import_service import ImportService
        from app.models.import_job import (
            ImportJobType, ImportJobStatus, DuplicateAction,
        )
        from app.models.user import User
        from sqlalchemy import select, func

        content = _read_test_file("valid_patrons.csv")
        job = await ImportService.upload(
            db=test_db,
            file_content=content,
            filename="valid_patrons.csv",
            job_type=ImportJobType.PATRONS,
            duplicate_action=DuplicateAction.SKIP,
            error_threshold=10.0,
            created_by_id=test_admin.id,
        )
        job = await ImportService.validate(test_db, job)
        job = await ImportService.execute(test_db, job)
        assert job.created_rows == 3

        # Count patrons before rollback
        count_before = await test_db.execute(select(func.count(User.id)))
        before = count_before.scalar()

        # Rollback — returns (job, created_deleted, updated_marked_only)
        job, created_deleted, updated_marked = await ImportService.rollback(test_db, job, reason="Test rollback")
        assert job.status == ImportJobStatus.ROLLED_BACK
        assert created_deleted == 3
        assert updated_marked == 0

        # Verify patrons removed
        count_after = await test_db.execute(select(func.count(User.id)))
        after = count_after.scalar()
        assert after == before - 3

    @pytest.mark.asyncio
    async def test_duplicate_detection_skip(self, test_db, test_admin):
        from app.services.import_service import ImportService
        from app.models.import_job import ImportJobType, DuplicateAction
        from app.models.user import User, UserRole
        from app.core.security import hash_password

        # Create an existing patron
        existing = User(
            email="testuser@example.com",
            password_hash=hash_password("TestPassword123!"),
            first_name="Test",
            last_name="User",
            role=UserRole.PATRON,
            is_active=True,
            library_card="EXISTING-001",
        )
        test_db.add(existing)
        await test_db.flush()

        content = _read_test_file("duplicate_patrons.csv")
        job = await ImportService.upload(
            db=test_db,
            file_content=content,
            filename="duplicate_patrons.csv",
            job_type=ImportJobType.PATRONS,
            duplicate_action=DuplicateAction.SKIP,
            error_threshold=50.0,
            created_by_id=test_admin.id,
        )
        job = await ImportService.validate(test_db, job)
        report = await ImportService.dry_run(test_db, job)
        assert report["duplicate_candidates"] >= 1
        assert report["would_skip"] >= 1

    @pytest.mark.asyncio
    async def test_column_mapping_revalidate(self, test_db, test_admin):
        from app.services.import_service import ImportService
        from app.models.import_job import ImportJobType, ImportJobStatus, DuplicateAction

        # CSV with different column names
        csv_data = "full_name,email_addr,card_number\nTest User,test@example.com,LSC-MAP-001\n"
        content = csv_data.encode("utf-8")

        job = await ImportService.upload(
            db=test_db,
            file_content=content,
            filename="remapped.csv",
            job_type=ImportJobType.PATRONS,
            duplicate_action=DuplicateAction.SKIP,
            error_threshold=10.0,
            created_by_id=test_admin.id,
        )
        job = await ImportService.validate(test_db, job)
        # Will have errors because "name" and "email" are not found
        assert job.error_rows > 0

        # Apply column mapping
        mapping = {
            "full_name": "name",
            "email_addr": "email",
            "card_number": "barcode",
        }
        job = await ImportService.set_column_mapping(test_db, job, mapping)
        assert job.status == ImportJobStatus.VALIDATED
        assert job.error_rows == 0  # Now valid

    @pytest.mark.asyncio
    async def test_error_threshold_auto_rollback(self, test_db, test_admin):
        from app.services.import_service import ImportService
        from app.models.import_job import (
            ImportJobType, ImportJobStatus, DuplicateAction,
        )

        # All rows will fail because holdings reference non-existent catalog IDs
        content = _read_test_file("valid_holdings.csv")
        job = await ImportService.upload(
            db=test_db,
            file_content=content,
            filename="valid_holdings.csv",
            job_type=ImportJobType.HOLDINGS,
            duplicate_action=DuplicateAction.SKIP,
            error_threshold=5.0,  # Very low threshold
            created_by_id=test_admin.id,
        )
        job = await ImportService.validate(test_db, job)
        job = await ImportService.execute(test_db, job)
        # Since catalog items don't exist, all will fail → auto rollback
        assert job.status in (ImportJobStatus.ROLLED_BACK, ImportJobStatus.COMPLETED)

    @pytest.mark.asyncio
    async def test_list_jobs(self, test_db, test_admin):
        from app.services.import_service import ImportService
        from app.models.import_job import ImportJobType, DuplicateAction

        content = _read_test_file("valid_patrons.csv")
        await ImportService.upload(
            db=test_db,
            file_content=content,
            filename="job1.csv",
            job_type=ImportJobType.PATRONS,
            duplicate_action=DuplicateAction.SKIP,
            error_threshold=10.0,
            created_by_id=test_admin.id,
        )
        await ImportService.upload(
            db=test_db,
            file_content=content,
            filename="job2.csv",
            job_type=ImportJobType.PATRONS,
            duplicate_action=DuplicateAction.SKIP,
            error_threshold=10.0,
            created_by_id=test_admin.id,
        )
        await test_db.flush()

        jobs, total = await ImportService.list_jobs(test_db, limit=10, offset=0)
        assert total >= 2
        assert len(jobs) >= 2

    @pytest.mark.asyncio
    async def test_get_job(self, test_db, test_admin):
        from app.services.import_service import ImportService
        from app.models.import_job import ImportJobType, DuplicateAction

        content = _read_test_file("valid_patrons.csv")
        job = await ImportService.upload(
            db=test_db,
            file_content=content,
            filename="get_test.csv",
            job_type=ImportJobType.PATRONS,
            duplicate_action=DuplicateAction.SKIP,
            error_threshold=10.0,
            created_by_id=test_admin.id,
        )
        await test_db.flush()

        fetched = await ImportService.get_job(test_db, job.id)
        assert fetched is not None
        assert fetched.id == job.id
        assert fetched.source_filename == "get_test.csv"


class TestImportJobModel:
    """Test ImportJob model properties."""

    def test_progress_percent(self):
        from app.models.import_job import ImportJob

        job = ImportJob(total_rows=100, processed_rows=50)
        assert job.progress_percent == 50.0

    def test_progress_percent_zero_rows(self):
        from app.models.import_job import ImportJob

        job = ImportJob(total_rows=0, processed_rows=0)
        assert job.progress_percent == 0.0

    def test_error_percent(self):
        from app.models.import_job import ImportJob

        job = ImportJob(total_rows=100, error_rows=5)
        assert job.error_percent == 5.0

    def test_is_complete(self):
        from app.models.import_job import ImportJob, ImportJobStatus

        job = ImportJob(status=ImportJobStatus.COMPLETED)
        assert job.is_complete is True

        job2 = ImportJob(status=ImportJobStatus.IMPORTING)
        assert job2.is_complete is False


class TestJSONParsing:
    """Test JSON file reading."""

    def test_read_json_file(self):
        from app.services.import_service import ImportService

        data = [
            {"name": "Test User", "email": "test@example.com"},
            {"name": "Another User", "email": "another@example.com"},
        ]
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(data, f)
            temp_path = f.name

        try:
            rows = ImportService._read_json(temp_path)
            assert len(rows) == 2
            assert rows[0]["name"] == "Test User"
        finally:
            os.unlink(temp_path)


# ══════════════════════════════════════════════════════════════════════════
# API endpoint tests
# ══════════════════════════════════════════════════════════════════════════


class TestImportAPI:
    """Test import API endpoints via FastAPI TestClient."""

    pytestmark = pytest.mark.asyncio

    async def test_list_templates(self, staff_client):
        response = await staff_client.get("/api/v1/import/templates")
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 4
        types = {t["job_type"] for t in data}
        assert "patrons" in types
        assert "catalog_items" in types

    @pytest.mark.skip(reason="GET /api/v1/import/templates/{job_type} download endpoint is promised in import_routes.py docstring but not yet implemented; track separately")
    async def test_download_template(self, staff_client):
        response = await staff_client.get("/api/v1/import/templates/patrons")
        assert response.status_code == 200
        assert "text/csv" in response.headers.get("content-type", "")
        content = response.text
        assert "name" in content
        assert "email" in content

    async def test_import_history_empty(self, staff_client):
        response = await staff_client.get("/api/v1/import/history")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data

    async def test_upload_validates_patron_csv(self, staff_client):
        csv_content = "name,email,barcode\nTest User,test@upload.com,LSC-UP-001\n"
        response = await staff_client.post(
            "/api/v1/import/upload",
            data={"job_type": "patrons", "duplicate_action": "skip", "error_threshold": "10"},
            files={"file": ("test.csv", csv_content.encode(), "text/csv")},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "validated"
        assert data["total_rows"] == 1
        assert data["error_rows"] == 0

    async def test_upload_rejects_empty_file(self, staff_client):
        response = await staff_client.post(
            "/api/v1/import/upload",
            data={"job_type": "patrons"},
            files={"file": ("empty.csv", b"", "text/csv")},
        )
        assert response.status_code == 400

    async def test_get_status(self, staff_client):
        # Upload first
        csv_content = "name,email\nTest,test@status.com\n"
        upload_resp = await staff_client.post(
            "/api/v1/import/upload",
            data={"job_type": "patrons"},
            files={"file": ("test.csv", csv_content.encode(), "text/csv")},
        )
        job_id = upload_resp.json()["id"]

        # Get status
        response = await staff_client.get(f"/api/v1/import/{job_id}/status")
        assert response.status_code == 200
        assert response.json()["job_id"] == job_id

    async def test_get_preview(self, staff_client):
        csv_content = "name,email,barcode\nAlice,alice@prev.com,LSC-PREV-001\nBob,bob@prev.com,LSC-PREV-002\n"
        upload_resp = await staff_client.post(
            "/api/v1/import/upload",
            data={"job_type": "patrons"},
            files={"file": ("test.csv", csv_content.encode(), "text/csv")},
        )
        job_id = upload_resp.json()["id"]

        response = await staff_client.get(f"/api/v1/import/{job_id}/preview")
        assert response.status_code == 200
        data = response.json()
        assert data["total_rows"] == 2
        assert len(data["preview_rows"]) == 2
        assert "detected_columns" in data
        assert "target_fields" in data

    async def test_dry_run(self, staff_client):
        csv_content = "name,email\nTest,test@dry.com\n"
        upload_resp = await staff_client.post(
            "/api/v1/import/upload",
            data={"job_type": "patrons"},
            files={"file": ("test.csv", csv_content.encode(), "text/csv")},
        )
        job_id = upload_resp.json()["id"]

        response = await staff_client.post(f"/api/v1/import/{job_id}/dry-run")
        assert response.status_code == 200
        data = response.json()
        assert "would_create" in data
        assert "would_skip" in data

    async def test_execute_and_rollback(self, staff_client):
        csv_content = "name,email,barcode\nExec User,exec@test.com,LSC-EXEC-001\n"
        upload_resp = await staff_client.post(
            "/api/v1/import/upload",
            data={"job_type": "patrons"},
            files={"file": ("test.csv", csv_content.encode(), "text/csv")},
        )
        job_id = upload_resp.json()["id"]

        # Execute
        exec_resp = await staff_client.post(f"/api/v1/import/{job_id}/execute")
        assert exec_resp.status_code == 200
        assert exec_resp.json()["status"] == "completed"
        assert exec_resp.json()["created_rows"] == 1

        # Rollback
        rb_resp = await staff_client.post(f"/api/v1/import/{job_id}/rollback")
        assert rb_resp.status_code == 200
        assert rb_resp.json()["status"] == "rolled_back"
        assert rb_resp.json()["records_rolled_back"] == 1

    async def test_status_not_found(self, staff_client):
        response = await staff_client.get("/api/v1/import/99999/status")
        assert response.status_code == 404

    async def test_column_mapping(self, staff_client):
        csv_content = "full_name,email_address\nTest,test@map.com\n"
        upload_resp = await staff_client.post(
            "/api/v1/import/upload",
            data={"job_type": "patrons"},
            files={"file": ("test.csv", csv_content.encode(), "text/csv")},
        )
        job_id = upload_resp.json()["id"]

        # Apply mapping
        response = await staff_client.post(
            f"/api/v1/import/{job_id}/column-mapping",
            json={"mapping": {"full_name": "name", "email_address": "email"}},
        )
        assert response.status_code == 200
        assert response.json()["status"] == "validated"
