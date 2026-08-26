"""Walks through a realistic session against the SIMULATED rig pool: two
users competing for rigs (one gets queued), a health sweep that takes a
rig out of service, running test suites against the mock apps (including
the seeded flaky/failing cases), and the resulting reports.
"""
from rig_pool import RigPool
from health import run_health_sweep
from test_runner import TestRunner
from reporting import print_reports


def main():
    pool = RigPool(rig_ids=["rig-01", "rig-02"])
    runner = TestRunner(pool)

    # User A checks out rig-01 and runs the Keyboard suite (repeated 5x to
    # surface the seeded voice_input_toggle flakiness).
    for i in range(5):
        rig_id, records = runner.run_suite("alice", "Keyboard", case_ids=["voice_input_toggle"], app_seed=i)
        print(f"alice run {i}: rig={rig_id} -> {[r.result for r in records]}")

    # User B checks out rig-02 (the other free rig) and runs Smartlight —
    # brightness_ramp is a seeded deterministic failure, a real bug to flag.
    rig_id, records = runner.run_suite("bob", "Smartlight")
    print(f"\nbob: rig={rig_id} -> " + ", ".join(f"{r.case_id}={r.result}" for r in records))

    # Demonstrate the queueing path: both rigs are free again at this
    # point (run_suite releases after each call), so carol and dave check
    # out the two free rigs, leaving none free — erin's checkout() then
    # queues instead of returning a rig.
    carol_rig = pool.checkout("carol")
    dave_rig = pool.checkout("dave")
    queued = pool.checkout("erin")
    print(f"\ncarol got: {carol_rig}, dave got: {dave_rig}, erin queued: {queued is None}")

    # Releasing carol's rig immediately serves erin next (FIFO) rather
    # than leaving it FREE for whoever calls checkout() next.
    next_user = pool.release(carol_rig, "carol")
    print(f"released {carol_rig}; next served: {next_user}")

    # Health sweep: rig-02 fails 3 checks in a row and gets quarantined.
    pool.release(dave_rig, "dave")
    pool.release(carol_rig, next_user)

    def flaky_health_check(rig_id):
        return rig_id != "rig-02"  # rig-02 always reports unhealthy here

    for _ in range(3):
        newly_faulty = run_health_sweep(pool, flaky_health_check)
    print(f"\nnewly faulty after repeated failing checks: {newly_faulty}")

    # A GlobalSearch run to add more data to the report.
    runner.run_suite("frank", "GlobalSearch", app_seed=1)

    print()
    print_reports(pool, runner)


if __name__ == "__main__":
    main()
