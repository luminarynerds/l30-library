import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select, func
from app.main import app
from app.core.database import get_db
from app.models.user import User, UserRole
from app.models.multi_branch import SystemSettings
from app.models.ai_config import AIConfiguration


@pytest.mark.asyncio
async def test_full_setup_bootstrap_sequence(db, tmp_path, monkeypatch):
    """Drive the EXACT wizard submit sequence end to end, unmocked, against the
    test DB. branding path is patched to tmp so we never touch prod branding.json."""
    # app.api.v1.setup.__init__ re-exports the `router` OBJECT, which shadows the
    # `router` submodule for both string paths and `import ... as`. importlib
    # returns the real module from sys.modules, so we can patch its global.
    import importlib

    setup_router_mod = importlib.import_module("app.api.v1.setup.router")
    monkeypatch.setattr(setup_router_mod, "_branding_path", lambda: tmp_path / "branding.json")

    async def _db():
        yield db

    app.dependency_overrides[get_db] = _db
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            r = await ac.post(
                "/api/v1/setup/admin",
                json={
                    "first_name": "Moira",
                    "last_name": "Rose",
                    "email": "moira@schittcreek.org",
                    "password": "roseapothecary",
                },
            )
            assert r.status_code == 201, r.text

            # Once the founding admin exists the remaining wizard steps are
            # admin-gated (require_setup_access, 2026-07-08). The bootstrap
            # response auto-logins by returning an access token; carry it
            # exactly as the wizard frontend does.
            auth = {"Authorization": f"Bearer {r.json()['access_token']}"}

            r = await ac.post(
                "/api/v1/setup/library-info",
                headers=auth,
                json={
                    "name": "Schitt Creek PL",
                    "code": "SCPL",
                    "email": "hi@schittcreek.org",
                    "phone": "555-0100",
                    "address": "1 Rose St",
                },
            )
            assert r.status_code == 200, r.text

            r = await ac.post(
                "/api/v1/setup/branding",
                headers=auth,
                json={
                    "primary_color": "#8B5E5E",
                    "accent_color": "#D49898",
                    "hero_title": "Welcome to Schitt Creek PL",
                    "tagline": "A little town",
                },
            )
            assert r.status_code == 200, r.text

            r = await ac.post(
                "/api/v1/setup/features",
                headers=auth,
                json={"preset": "small_library", "overrides": {"events_enabled": True}},
            )
            assert r.status_code == 200, r.text

            r = await ac.post(
                "/api/v1/setup/ai",
                headers=auth,
                json={
                    "model": "qwen2.5:0.5b",
                    "temperature": 0.7,
                    "system_prompt": "Be kind.",
                    "guardrails": {},
                },
            )
            assert r.status_code == 200, r.text

            # features GET is public; verify persistence reflects what we sent
            r = await ac.get("/api/v1/organization-features")
            assert r.status_code == 200, r.text
            feats = r.json()
            assert feats["events_enabled"] is True  # our override
            assert feats["front_desk_enabled"] is True  # in small_library preset

            r = await ac.post("/api/v1/setup/complete", headers=auth, json={})
            assert r.status_code == 200, r.text

        # end state in the DB
        admins = await db.scalar(
            select(func.count(User.id)).where(User.role == UserRole.SUPER_ADMIN)
        )
        assert admins == 1
        ss = (
            await db.execute(select(SystemSettings).order_by(SystemSettings.id.desc()).limit(1))
        ).scalar_one()
        assert ss.setup_complete is True
        agent = (
            await db.execute(
                select(AIConfiguration).where(AIConfiguration.config_key == "agent_chat")
            )
        ).scalar_one()
        assert agent.config_value["model"] == "qwen2.5:0.5b"
        assert agent.config_value["system_prompt"] == "Be kind."
        ollama = (
            await db.execute(select(AIConfiguration).where(AIConfiguration.config_key == "ollama"))
        ).scalar_one()
        assert ollama.config_value["model"] == "qwen2.5:0.5b"
    finally:
        app.dependency_overrides.pop(get_db, None)
