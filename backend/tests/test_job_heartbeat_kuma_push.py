# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tests for the Kuma push side of the scheduler heartbeat (_push_to_kuma).

The push is the positive heartbeat: it pings an Uptime Kuma push monitor every
run so Kuma alerts when the pings stop. These cover the URL/params it builds,
the up/down status, the no-op when unconfigured, and that a monitoring outage
is swallowed rather than breaking the heartbeat check.
"""
from types import SimpleNamespace

import pytest

from app.services.schedulers import job_heartbeat


class _Recorder:
    def __init__(self):
        self.calls = []


def _fake_client(recorder, raise_exc=None):
    class FakeResp:
        def raise_for_status(self):
            pass

    class FakeClient:
        def __init__(self, *a, **k):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def get(self, url, params=None):
            recorder.calls.append((url, params))
            if raise_exc:
                raise raise_exc
            return FakeResp()

    return FakeClient


def _set_settings(monkeypatch, token):
    monkeypatch.setattr(
        job_heartbeat,
        "settings",
        SimpleNamespace(
            kuma_heartbeat_push_token=token,
            kuma_base_url="http://uptime-kuma:3001",
        ),
    )


@pytest.mark.asyncio
async def test_push_noop_when_token_unset(monkeypatch):
    rec = _Recorder()
    _set_settings(monkeypatch, "")
    monkeypatch.setattr(job_heartbeat.httpx, "AsyncClient", _fake_client(rec))

    await job_heartbeat._push_to_kuma(True, "all 10 healthy")

    assert rec.calls == []


@pytest.mark.asyncio
async def test_push_up_builds_correct_request(monkeypatch):
    rec = _Recorder()
    _set_settings(monkeypatch, "tok123")
    monkeypatch.setattr(job_heartbeat.httpx, "AsyncClient", _fake_client(rec))

    await job_heartbeat._push_to_kuma(True, "all 10 critical jobs healthy")

    assert len(rec.calls) == 1
    url, params = rec.calls[0]
    assert url == "http://uptime-kuma:3001/api/push/tok123"
    assert params == {"status": "up", "msg": "all 10 critical jobs healthy"}


@pytest.mark.asyncio
async def test_push_down_status(monkeypatch):
    rec = _Recorder()
    _set_settings(monkeypatch, "tok")
    monkeypatch.setattr(job_heartbeat.httpx, "AsyncClient", _fake_client(rec))

    await job_heartbeat._push_to_kuma(False, "2 job(s) overdue: x, y")

    assert rec.calls[0][1]["status"] == "down"


@pytest.mark.asyncio
async def test_push_swallows_monitoring_outage(monkeypatch):
    rec = _Recorder()
    _set_settings(monkeypatch, "tok")
    monkeypatch.setattr(
        job_heartbeat.httpx,
        "AsyncClient",
        _fake_client(rec, raise_exc=RuntimeError("kuma down")),
    )

    # Must not raise: a monitoring outage cannot break the heartbeat check.
    await job_heartbeat._push_to_kuma(True, "all healthy")
