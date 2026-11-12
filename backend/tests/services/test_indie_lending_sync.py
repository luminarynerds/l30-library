"""Sync-state tracking for the L30 -> MetisLib borrow/return mirror."""
import pytest
from datetime import datetime, timezone, timedelta

from app.models.indie_ebook_borrow import (
    IndieEbook, IndieEbookBorrow, BorrowStatus, MetisLibSyncState,
)
from app.services.indie_lending_service import IndieLendingService


# --- Task 3: enum + column ---------------------------------------------------

def test_sync_state_enum_values():
    assert MetisLibSyncState.not_required.value == "not_required"
    assert MetisLibSyncState.synced.value == "synced"
    assert MetisLibSyncState.borrow_failed.value == "borrow_failed"
    assert MetisLibSyncState.return_failed.value == "return_failed"


def test_borrow_defaults_to_not_required():
    b = IndieEbookBorrow()
    assert b.metislib_sync_state in (None, MetisLibSyncState.not_required)


# --- Task 4: service records the sync outcome --------------------------------

def _fake_client(*, borrow_id=None, raises=False):
    class _C:
        async def borrow_indie(self, mid, ph):
            if raises:
                raise RuntimeError("MetisLib down")
            return {"borrow_id": borrow_id}

        async def return_indie(self, mid, ph):
            if raises:
                raise RuntimeError("MetisLib down")
            return {"status": "returned"}
    return _C()


@pytest.mark.asyncio
async def test_borrow_local_only_title_is_not_required(db, test_patron):
    ebook = IndieEbook(title="Local Only", metislib_ebook_id=None)
    db.add(ebook)
    await db.flush()
    borrow = await IndieLendingService().borrow_ebook(ebook.id, test_patron.id, db)
    assert borrow.metislib_sync_state == MetisLibSyncState.not_required


@pytest.mark.asyncio
async def test_borrow_synced_when_metislib_succeeds(db, test_patron, monkeypatch):
    ebook = IndieEbook(title="Synced", metislib_ebook_id=4321)
    db.add(ebook)
    await db.flush()
    monkeypatch.setattr(
        "app.services.metislib_client.get_metislib_client",
        lambda: _fake_client(borrow_id=99),
    )
    borrow = await IndieLendingService().borrow_ebook(ebook.id, test_patron.id, db)
    assert borrow.metislib_borrow_id == 99
    assert borrow.metislib_sync_state == MetisLibSyncState.synced


@pytest.mark.asyncio
async def test_borrow_marks_failed_when_metislib_raises(db, test_patron, monkeypatch):
    ebook = IndieEbook(title="Drift", metislib_ebook_id=4321)
    db.add(ebook)
    await db.flush()
    monkeypatch.setattr(
        "app.services.metislib_client.get_metislib_client",
        lambda: _fake_client(raises=True),
    )
    borrow = await IndieLendingService().borrow_ebook(ebook.id, test_patron.id, db)
    assert borrow.metislib_borrow_id is None
    assert borrow.metislib_sync_state == MetisLibSyncState.borrow_failed  # not silent


@pytest.mark.asyncio
async def test_return_marks_failed_when_metislib_raises(db, test_patron, monkeypatch):
    ebook = IndieEbook(title="Drift2", metislib_ebook_id=4321)
    db.add(ebook)
    await db.flush()
    borrow = IndieEbookBorrow(
        ebook_id=ebook.id, user_id=test_patron.id,
        due_at=datetime.now(timezone.utc) + timedelta(days=21),
        access_token="tok-return", status=BorrowStatus.active,
        metislib_borrow_id=99, metislib_sync_state=MetisLibSyncState.synced,
    )
    db.add(borrow)
    await db.flush()
    monkeypatch.setattr(
        "app.services.metislib_client.get_metislib_client",
        lambda: _fake_client(raises=True),
    )
    out = await IndieLendingService().return_ebook(borrow, rating=None, db=db)
    assert out.metislib_sync_state == MetisLibSyncState.return_failed


# --- Task 5: reconcile job retries failed syncs ------------------------------

class _SessionCtx:
    """Async-context wrapper yielding the test session without closing it."""
    def __init__(self, session):
        self._s = session

    async def __aenter__(self):
        return self._s

    async def __aexit__(self, *a):
        return False


@pytest.mark.asyncio
async def test_reconcile_retries_failed_borrow_sync(db, test_patron, monkeypatch):
    from app.services.schedulers.indie_lending_jobs import reconcile_metislib_borrow_sync
    ebook = IndieEbook(title="Retry me", metislib_ebook_id=4321)
    db.add(ebook)
    await db.flush()
    borrow = IndieEbookBorrow(
        ebook_id=ebook.id, user_id=test_patron.id,
        due_at=datetime.now(timezone.utc) + timedelta(days=21),
        access_token="tok-recon", status=BorrowStatus.active,
        metislib_sync_state=MetisLibSyncState.borrow_failed,
    )
    db.add(borrow)
    await db.flush()
    monkeypatch.setattr(
        "app.services.metislib_client.get_metislib_client",
        lambda: _fake_client(borrow_id=777),
    )
    monkeypatch.setattr(
        "app.services.schedulers.indie_lending_jobs.AsyncSessionLocal",
        lambda: _SessionCtx(db),
    )
    n = await reconcile_metislib_borrow_sync()
    await db.refresh(borrow)
    assert borrow.metislib_sync_state == MetisLibSyncState.synced
    assert borrow.metislib_borrow_id == 777
    assert n == 1
