"""Locust load profile for the SIM Provisioning activation flow.

Headless example:
    locust -f scripts/load-test-locustfile.py --headless -u 50 -r 10 -t 60s \
           --host http://localhost:8000

Targets ~50 RPS for 60s by spawning 50 users at 10 users/s with a tight
think-time. The activation task weights match the production traffic mix
observed in staging: 70% reads, 25% activations, 5% suspends.
"""
from __future__ import annotations

import random
import string
import uuid

from locust import HttpUser, between, events, task


def _rand_iccid() -> str:
    return "8991" + "".join(random.choices(string.digits, k=15))


def _rand_msisdn() -> str:
    return "+9198" + "".join(random.choices(string.digits, k=8))


@events.quitting.add_listener
def _exit_nonzero_on_failures(environment, **_kwargs) -> None:
    stats = environment.stats
    if stats.total.fail_ratio > 0.01:
        environment.process_exit_code = 1
    elif stats.total.get_response_time_percentile(0.95) > 2000:
        environment.process_exit_code = 1


class OperatorUser(HttpUser):
    wait_time = between(0.5, 1.5)

    def on_start(self) -> None:
        self.client.headers.update({"x-request-id": str(uuid.uuid4())})

    @task(14)
    def list_sims(self) -> None:
        self.client.get("/sims?limit=20", name="/sims")

    @task(5)
    def activate(self) -> None:
        payload = {
            "iccid":  _rand_iccid(),
            "msisdn": _rand_msisdn(),
            "plan_id": random.choice(["plan-lite", "plan-standard", "plan-pro"]),
        }
        with self.client.post("/sims/activate", json=payload,
                              name="/sims/activate",
                              catch_response=True) as r:
            if r.status_code not in (200, 201, 202):
                r.failure(f"unexpected {r.status_code}: {r.text[:160]}")

    @task(1)
    def suspend(self) -> None:
        iccid = _rand_iccid()
        self.client.post(f"/sims/{iccid}/suspend", name="/sims/:iccid/suspend")

    @task(2)
    def health(self) -> None:
        self.client.get("/healthz", name="/healthz")
