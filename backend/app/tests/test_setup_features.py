import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.core.database import get_db
from app.models.user import User, UserRole
from app.core.security import create_access_token, hash_password


@pytest.fixture
async def founding_admin(db):
    user = User(
        first_name="Ada",
        last_name="Lovelace",
        email="ada@lib.test",
        password_hash=hash_password("password123"),
        role=UserRole.SUPER_ADMIN,
        is_active=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


def _override_db(db):
    async def _db():
        yield db

    app.dependency_overrides[get_db] = _db


def _auth_headers(user):
    # Once a founding admin exists, /setup/* is admin-gated
    # (require_setup_access, 2026-07-08); authenticate the same way the
    # wizard does after auto-login.
    token = create_access_token(subject=user.id, email=user.email, role=user.role.value)
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_setup_features_applies_preset(db, founding_admin):
    _override_db(db)
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.post(
                "/api/v1/setup/features",
                headers=_auth_headers(founding_admin),
                json={"preset": "small_library", "overrides": {"events_enabled": True}},
            )
        assert resp.status_code == 200
        body = resp.json()
        assert body["events_enabled"] is True
        assert body["front_desk_enabled"] is True
    finally:
        app.dependency_overrides.pop(get_db, None)


@pytest.mark.asyncio
async def test_setup_features_rejects_unknown_preset(db, founding_admin):
    _override_db(db)
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.post(
                "/api/v1/setup/features",
                headers=_auth_headers(founding_admin),
                json={"preset": "medium", "overrides": {}},
            )
        assert resp.status_code == 400
    finally:
        app.dependency_overrides.pop(get_db, None)


@pytest.mark.asyncio
async def test_setup_features_requires_founding_admin(db):
    _override_db(db)
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.post("/api/v1/setup/features", json={"preset": "full", "overrides": {}})
        assert resp.status_code == 400
    finally:
        app.dependency_overrides.pop(get_db, None)
