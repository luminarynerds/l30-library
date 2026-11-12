# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Verify the dev/test-only async lazy-load guard.

With the guard installed, an implicit relationship lazy-load raises
AsyncLazyLoadInResponseError. With selectinload(), no error.
"""
from __future__ import annotations

import pytest
from sqlalchemy import Column, ForeignKey, Integer, String, select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import DeclarativeBase, relationship, selectinload, sessionmaker

from app.core.lazy_load_guard import (
    AsyncLazyLoadInResponseError,
    install_lazy_load_guard,
)


class _Base(AsyncAttrs, DeclarativeBase):
    pass


class _Parent(_Base):
    __tablename__ = "llg_parent"
    id = Column(Integer, primary_key=True)
    name = Column(String(50))
    children = relationship("_Child", back_populates="parent", lazy="select")


class _Child(_Base):
    __tablename__ = "llg_child"
    id = Column(Integer, primary_key=True)
    parent_id = Column(Integer, ForeignKey("llg_parent.id"))
    parent = relationship("_Parent", back_populates="children")


@pytest.fixture
async def session(monkeypatch):
    # Force guard install regardless of process env.
    from app.core import lazy_load_guard as g
    from app.core import config as cfg

    s = cfg.get_settings()
    monkeypatch.setattr(s, "environment", "test", raising=False)
    monkeypatch.setattr(g.install_lazy_load_guard, "_installed", False, raising=False)
    install_lazy_load_guard()

    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(_Base.metadata.create_all)
    Session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with Session() as session:
        p = _Parent(name="p")
        p.children = [_Child(), _Child()]
        session.add(p)
        await session.commit()
        yield session
    await engine.dispose()


@pytest.mark.asyncio
async def test_lazy_load_raises_actionable_error(session):
    # Re-query without selectinload — children is unloaded.
    parent = (await session.execute(select(_Parent))).scalar_one()
    session.expire(parent, ["children"])
    with pytest.raises(AsyncLazyLoadInResponseError) as excinfo:
        _ = await parent.awaitable_attrs.children
    msg = str(excinfo.value)
    assert "_Parent" in msg
    assert "children" in msg
    assert "selectinload" in msg


@pytest.mark.asyncio
async def test_selectinload_does_not_raise(session):
    parent = (
        await session.execute(select(_Parent).options(selectinload(_Parent.children)))
    ).scalar_one()
    # Already loaded — no implicit lazy-load.
    children = list(parent.children)
    assert len(children) == 2
