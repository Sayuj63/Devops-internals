from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_healthz(client):
    r = await client.get("/healthz")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_readyz(client):
    r = await client.get("/readyz")
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_metrics_exposed(client):
    r = await client.get("/metrics")
    assert r.status_code == 200
    assert "sim_state_transitions_total" in r.text or "python_info" in r.text


@pytest.mark.asyncio
async def test_request_id_header(client):
    r = await client.get("/healthz")
    assert "x-request-id" in {k.lower() for k in r.headers.keys()}


@pytest.mark.asyncio
async def test_list_sims_empty(client):
    r = await client.get("/api/v1/sims")
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 0
    assert body["items"] == []


@pytest.mark.asyncio
async def test_allocate_and_activate_flow(client, seeded):
    iccid = seeded["sims"][0].iccid

    r = await client.post(
        f"/api/v1/sims/{iccid}/allocate",
        json={"actor": "tester", "reason": "test alloc"},
    )
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "ALLOCATED"

    r = await client.post(
        f"/api/v1/sims/{iccid}/activate",
        json={"actor": "tester", "reason": "test activate"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "ACTIVE"
    assert body["msisdn"] is not None
    assert body["provisioning_ref"] is not None


@pytest.mark.asyncio
async def test_bad_iccid_returns_422(client):
    r = await client.post(
        "/api/v1/sims/12345/allocate",
        json={"actor": "tester"},
    )
    assert r.status_code == 422
    body = r.json()
    assert body["status"] == 422
    assert "iccid" in body["detail"].lower() or "ICCID" in body["detail"]


@pytest.mark.asyncio
async def test_invalid_transition_returns_409(client, seeded):
    iccid = seeded["sims"][0].iccid
    r = await client.post(
        f"/api/v1/sims/{iccid}/activate",
        json={"actor": "tester"},
    )
    assert r.status_code == 409
    assert r.json()["title"] == "Invalid SIM state transition"


@pytest.mark.asyncio
async def test_list_plans(client, seeded):
    r = await client.get("/api/v1/plans")
    assert r.status_code == 200
    plans = r.json()
    assert len(plans) >= 1
    assert plans[0]["name"]


@pytest.mark.asyncio
async def test_stats_endpoint(client, seeded):
    r = await client.get("/api/v1/stats")
    assert r.status_code == 200
    body = r.json()
    assert body["total_sims"] == 10
    assert body["msisdn_pool_remaining"] == 5
    assert any(c["status"] == "PENDING" for c in body["counts_by_status"])


@pytest.mark.asyncio
async def test_audit_feed(client, seeded):
    iccid = seeded["sims"][0].iccid
    await client.post(
        f"/api/v1/sims/{iccid}/allocate", json={"actor": "tester"}
    )
    r = await client.get("/api/v1/audit?limit=10")
    assert r.status_code == 200
    body = r.json()
    assert body["total"] >= 1
    assert body["items"][0]["to_status"] == "ALLOCATED"


@pytest.mark.asyncio
async def test_bulk_provision(client, seeded):
    # Use a known-good Luhn-valid ICCID and a fresh IMSI.
    from app.seed import _gen_iccid, _gen_imsi
    import random

    rng = random.Random(999)
    new_iccid = _gen_iccid(rng)
    new_imsi = _gen_imsi(rng, 9999)
    r = await client.post(
        "/api/v1/sims/bulk_provision",
        json={
            "items": [
                {"iccid": new_iccid, "imsi": new_imsi},
            ],
            "actor": "bulk-test",
        },
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["inserted"] == 1
