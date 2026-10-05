"""Simulated health checks for rigs in the pool — models operating,
maintaining, and fault-analyzing test environments.

A real implementation would ping actual hardware (serial console, network
reachability, a heartbeat app on the head unit, etc.). Here, health check
results are provided by a pluggable `health_check_fn(rig_id) -> bool` so
the logic (consecutive-failure threshold -> automatic quarantine) can be
tested deterministically without needing real hardware to poll.
"""
from rig_pool import RigPool, RigStatus

DEFAULT_FAILURE_THRESHOLD = 3


def run_health_check(pool: RigPool, rig_id: str, is_healthy: bool, threshold: int = DEFAULT_FAILURE_THRESHOLD):
    """Records one health-check result for a rig. If the rig is currently
    IN_USE or RESERVED, a failing check does NOT immediately fault it out
    from under an active user — it's flagged for the next available
    window instead (consecutive_health_failures still increments, so it
    still quarantines once free and the threshold trips). This mirrors a
    real ops decision: don't yank hardware out from under someone mid-
    session over a single flaky ping.
    """
    rig = pool.rigs[rig_id]

    if is_healthy:
        rig.consecutive_health_failures = 0
        return

    rig.consecutive_health_failures += 1
    if rig.consecutive_health_failures >= threshold and rig.status in (RigStatus.FREE, RigStatus.MAINTENANCE):
        pool.mark_faulty(rig_id)


def run_health_sweep(pool: RigPool, health_check_fn, threshold: int = DEFAULT_FAILURE_THRESHOLD):
    """Runs a health check across every rig currently known to the pool,
    using health_check_fn(rig_id) -> bool to get each result. Returns the
    list of rig_ids newly marked FAULTY by this sweep."""
    newly_faulty = []
    for rig_id, rig in pool.rigs.items():
        was_faulty = rig.status == RigStatus.FAULTY
        run_health_check(pool, rig_id, health_check_fn(rig_id), threshold)
        if not was_faulty and rig.status == RigStatus.FAULTY:
            newly_faulty.append(rig_id)
    return newly_faulty
