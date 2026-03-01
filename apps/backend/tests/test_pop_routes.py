"""Regression tests for routes/pop.py — the Pop grocery savings agent.

Covers health check and smoke test for the assembled router.
Full endpoint tests live in:
  test_pop_list.py     — list, invite, item CRUD, offer claims
  test_pop_wallet.py   — wallet, receipt scan
  test_pop_chat.py     — web chat
  test_pop_webhooks.py — Resend + Twilio webhook handlers
  test_pop_helpers.py  — helper unit tests
  test_pop_referral.py — referral endpoints
"""
import pytest
from httpx import AsyncClient


# ---------------------------------------------------------------------------
# 1. Health check
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_health_check(client: AsyncClient):
    resp = await client.get("/pop/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["service"] == "pop"
