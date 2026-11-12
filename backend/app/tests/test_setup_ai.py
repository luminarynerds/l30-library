import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select
from app.main import app
from app.core.database import get_db
from app.models.ai_config import AIConfiguration


def _override_db(db):
    async def _db():
        yield db
    app.dependency_overrides[get_db] = _db


@pytest.mark.asyncio
async def test_setup_ai_writes_agent_chat_and_ollama(db):
    _override_db(db)
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.post("/api/v1/setup/ai", json={
                "model": "llama3.2:1b", "temperature": 0.4,
                "system_prompt": "Be concise.", "guardrails": {"max_len": 500},
            })
        assert resp.status_code == 200
        agent = (await db.execute(
            select(AIConfiguration).where(AIConfiguration.config_key == "agent_chat")
        )).scalar_one()
        assert agent.config_value["model"] == "llama3.2:1b"
        assert agent.config_value["temperature"] == 0.4
        assert agent.config_value["system_prompt"] == "Be concise."
        ollama = (await db.execute(
            select(AIConfiguration).where(AIConfiguration.config_key == "ollama")
        )).scalar_one()
        assert ollama.config_value["model"] == "llama3.2:1b"
    finally:
        app.dependency_overrides.pop(get_db, None)


@pytest.mark.asyncio
async def test_setup_ai_merges_into_existing_ollama_config(db):
    existing = AIConfiguration(config_key="ollama", config_value={"base_url": "http://172.20.0.1:11434"})
    db.add(existing)
    await db.commit()
    _override_db(db)
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.post("/api/v1/setup/ai", json={
                "model": "qwen2.5:0.5b", "temperature": 0.7, "system_prompt": "", "guardrails": {},
            })
        assert resp.status_code == 200
        ollama = (await db.execute(
            select(AIConfiguration).where(AIConfiguration.config_key == "ollama")
        )).scalar_one()
        assert ollama.config_value["base_url"] == "http://172.20.0.1:11434"
        assert ollama.config_value["model"] == "qwen2.5:0.5b"
    finally:
        app.dependency_overrides.pop(get_db, None)
