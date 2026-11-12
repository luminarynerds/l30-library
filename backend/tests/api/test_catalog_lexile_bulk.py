import io
import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


async def test_bulk_import_updates_matched_isbns(staff_client: AsyncClient, books_with_isbns):
    csv = "isbn,lexile\n9780000000001,750L\n9780000000002,ad650l\n"
    files = {"file": ("lexile.csv", io.BytesIO(csv.encode()), "text/csv")}
    r = await staff_client.post("/api/v1/catalog/lexile/bulk-import", files=files)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["matched"] == 2
    assert body["updated"] == 2
    assert body["skipped_invalid"] == 0
    assert body["skipped_no_match"] == 0


async def test_bulk_import_reports_invalid_and_unmatched(staff_client, books_with_isbns):
    csv = "isbn,lexile\n9780000000001,L750\n9999999999999,400L\n"
    files = {"file": ("lexile.csv", io.BytesIO(csv.encode()), "text/csv")}
    r = await staff_client.post("/api/v1/catalog/lexile/bulk-import", files=files)
    assert r.status_code == 200
    body = r.json()
    assert body["skipped_invalid"] == 1
    assert body["skipped_no_match"] == 1
    assert body["updated"] == 0


async def test_bulk_import_rejects_non_staff(public_client):
    csv = "isbn,lexile\n9780000000001,750L\n"
    files = {"file": ("lexile.csv", io.BytesIO(csv.encode()), "text/csv")}
    r = await public_client.post("/api/v1/catalog/lexile/bulk-import", files=files)
    assert r.status_code in (401, 403)
