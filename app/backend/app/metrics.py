from __future__ import annotations

from prometheus_client import Counter, Gauge, Histogram

from app.config import get_settings

_settings = get_settings()

sim_state_transitions_total = Counter(
    "sim_state_transitions_total",
    "Count of SIM state transitions, labelled by from/to status.",
    labelnames=("from_status", "to_status"),
)

sim_activation_latency_seconds = Histogram(
    "sim_activation_latency_seconds",
    "Time from SIM allocation to activation in seconds.",
    buckets=_settings.activation_latency_buckets_seconds,
)

msisdn_pool_remaining = Gauge(
    "msisdn_pool_remaining",
    "Number of unallocated MSISDNs left in the pool.",
)

hlr_calls_total = Counter(
    "hlr_calls_total",
    "Total HLR/HSS provisioning calls by outcome.",
    labelnames=("outcome",),
)
