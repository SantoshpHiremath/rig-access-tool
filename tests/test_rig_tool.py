"""Test suite for the simulated remote test-rig access/tooling project."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from rig_pool import RigPool, RigStatus, RigCheckoutError
from health import run_health_check, run_health_sweep, DEFAULT_FAILURE_THRESHOLD
from test_apps import KeyboardApp, SmartlightApp, GlobalSearchApp, SettingsApp, TestResult, ALL_APPS
from test_runner import TestRunner
from reporting import pool_status_report, pass_rate_by_app, flaky_cases


# --- RigPool: checkout / release / queue ------------------------------------

def test_checkout_returns_a_free_rig():
    pool = RigPool(["r1", "r2"])
    rig_id = pool.checkout("alice")
    assert rig_id in ("r1", "r2")
    assert pool.rigs[rig_id].status == RigStatus.RESERVED
    assert pool.rigs[rig_id].held_by == "alice"


def test_checkout_queues_when_no_rig_free():
    pool = RigPool(["r1"])
    pool.checkout("alice")
    result = pool.checkout("bob")
    assert result is None
    assert pool.queue_depth() == 1


def test_release_frees_rig_when_queue_empty():
    pool = RigPool(["r1"])
    pool.checkout("alice")
    next_user = pool.release("r1", "alice")
    assert next_user is None
    assert pool.rigs["r1"].status == RigStatus.FREE
    assert pool.rigs["r1"].held_by is None


def test_release_serves_next_queued_user_fifo():
    pool = RigPool(["r1"])
    pool.checkout("alice")
    pool.checkout("bob")
    pool.checkout("carol")
    next_user = pool.release("r1", "alice")
    assert next_user == "bob"
    assert pool.rigs["r1"].status == RigStatus.RESERVED
    assert pool.rigs["r1"].held_by == "bob"
    assert pool.queue_depth() == 1  # carol still waiting


def test_release_by_wrong_user_raises():
    pool = RigPool(["r1"])
    pool.checkout("alice")
    with pytest.raises(RigCheckoutError):
        pool.release("r1", "bob")


def test_begin_use_requires_reservation_by_same_user():
    pool = RigPool(["r1"])
    pool.checkout("alice")
    with pytest.raises(RigCheckoutError):
        pool.begin_use("r1", "bob")
    pool.begin_use("r1", "alice")
    assert pool.rigs["r1"].status == RigStatus.IN_USE


def test_faulty_rig_never_handed_out_by_checkout():
    pool = RigPool(["r1", "r2"])
    pool.mark_faulty("r1")
    for _ in range(5):
        rig_id = pool.checkout(f"user-{_}")
        assert rig_id != "r1"
        pool.release(rig_id, f"user-{_}")


def test_clear_fault_returns_rig_to_free_and_resets_failure_count():
    pool = RigPool(["r1"])
    pool.mark_faulty("r1")
    pool.rigs["r1"].consecutive_health_failures = 5
    pool.clear_fault("r1")
    assert pool.rigs["r1"].status == RigStatus.FREE
    assert pool.rigs["r1"].consecutive_health_failures == 0


# --- Health checks -----------------------------------------------------------

def test_healthy_check_resets_failure_counter():
    pool = RigPool(["r1"])
    pool.rigs["r1"].consecutive_health_failures = 2
    run_health_check(pool, "r1", is_healthy=True)
    assert pool.rigs["r1"].consecutive_health_failures == 0


def test_repeated_failures_below_threshold_do_not_quarantine():
    pool = RigPool(["r1"])
    for _ in range(DEFAULT_FAILURE_THRESHOLD - 1):
        run_health_check(pool, "r1", is_healthy=False)
    assert pool.rigs["r1"].status == RigStatus.FREE


def test_repeated_failures_at_threshold_quarantines_rig():
    pool = RigPool(["r1"])
    for _ in range(DEFAULT_FAILURE_THRESHOLD):
        run_health_check(pool, "r1", is_healthy=False)
    assert pool.rigs["r1"].status == RigStatus.FAULTY


def test_failing_check_does_not_fault_a_rig_currently_in_use():
    pool = RigPool(["r1"])
    pool.checkout("alice")
    pool.begin_use("r1", "alice")
    for _ in range(DEFAULT_FAILURE_THRESHOLD + 2):
        run_health_check(pool, "r1", is_healthy=False)
    # still IN_USE — a real ops tool shouldn't yank hardware out from
    # under an active session over health-check failures alone.
    assert pool.rigs["r1"].status == RigStatus.IN_USE
    assert pool.rigs["r1"].consecutive_health_failures >= DEFAULT_FAILURE_THRESHOLD


def test_health_sweep_reports_newly_faulty_rigs_only():
    pool = RigPool(["r1", "r2"])
    always_unhealthy = lambda rig_id: False
    run_health_sweep(pool, always_unhealthy)
    run_health_sweep(pool, always_unhealthy)
    newly_faulty = run_health_sweep(pool, always_unhealthy)  # 3rd sweep crosses threshold
    assert set(newly_faulty) == {"r1", "r2"}
    # a 4th sweep should report nothing NEW (already faulty)
    newly_faulty_again = run_health_sweep(pool, always_unhealthy)
    assert newly_faulty_again == []


# --- Mock apps -----------------------------------------------------------------

def test_keyboard_deterministic_case_always_passes():
    app = KeyboardApp(seed=1)
    for _ in range(20):
        assert app.run_case("layout_switch_de_en") == TestResult.PASS


def test_keyboard_voice_toggle_is_flaky_across_seeds():
    outcomes = {KeyboardApp(seed=s).run_case("voice_input_toggle") for s in range(30)}
    assert TestResult.PASS in outcomes and TestResult.FAIL in outcomes


def test_smartlight_brightness_ramp_always_fails():
    app = SmartlightApp(seed=1)
    for _ in range(10):
        assert app.run_case("brightness_ramp") == TestResult.FAIL


def test_unknown_case_raises_value_error():
    app = SettingsApp()
    with pytest.raises(ValueError):
        app.run_case("nonexistent_case")


def test_all_apps_registry_matches_classes():
    assert ALL_APPS["Keyboard"] is KeyboardApp
    assert ALL_APPS["GlobalSearch"] is GlobalSearchApp


# --- TestRunner ----------------------------------------------------------------

def test_run_suite_returns_none_rig_when_queued():
    pool = RigPool(["r1"])
    runner = TestRunner(pool)
    pool.checkout("blocker")  # occupy the only rig
    rig_id, records = runner.run_suite("alice", "Settings")
    assert rig_id is None
    assert records == []


def test_run_suite_logs_one_record_per_case_and_releases_rig():
    pool = RigPool(["r1"])
    runner = TestRunner(pool)
    rig_id, records = runner.run_suite("alice", "Settings", timestamp_fn=lambda: 0.0)
    assert rig_id == "r1"
    assert len(records) == len(SettingsApp.test_cases)
    assert pool.rigs["r1"].status == RigStatus.FREE  # released after run
    assert len(runner.history) == len(SettingsApp.test_cases)


def test_run_suite_respects_explicit_case_subset():
    pool = RigPool(["r1"])
    runner = TestRunner(pool)
    _, records = runner.run_suite("alice", "Keyboard", case_ids=["autocorrect_suggestion"])
    assert len(records) == 1
    assert records[0].case_id == "autocorrect_suggestion"


def test_run_suite_unknown_app_raises():
    pool = RigPool(["r1"])
    runner = TestRunner(pool)
    with pytest.raises(ValueError):
        runner.run_suite("alice", "NotARealApp")


# --- Reporting -------------------------------------------------------------

def test_pool_status_report_matches_manual_counts():
    pool = RigPool(["r1", "r2", "r3"])
    pool.checkout("alice")
    pool.mark_faulty("r2")
    report = pool_status_report(pool)
    assert report["free"] == 1
    assert report["reserved"] == 1
    assert report["faulty"] == 1
    assert report["queue_depth"] == 0


def test_pass_rate_by_app_computes_correct_percentage():
    pool = RigPool(["r1"])
    runner = TestRunner(pool)
    runner.run_suite("alice", "Settings")  # all pass, deterministic
    report = pass_rate_by_app(runner)
    assert report["Settings"]["pass"] == len(SettingsApp.test_cases)
    assert report["Settings"]["fail"] == 0
    assert report["Settings"]["pass_rate_pct"] == 100.0


def test_flaky_cases_detects_inconsistent_case():
    pool = RigPool(["r1"])
    runner = TestRunner(pool)
    for seed in range(20):
        runner.run_suite("alice", "Keyboard", case_ids=["voice_input_toggle"], app_seed=seed)
    flaky = flaky_cases(runner)
    assert any(f["app"] == "Keyboard" and f["case"] == "voice_input_toggle" for f in flaky)


def test_flaky_cases_excludes_consistent_case():
    pool = RigPool(["r1"])
    runner = TestRunner(pool)
    for seed in range(20):
        runner.run_suite("alice", "Settings", case_ids=["wifi_toggle"], app_seed=seed)
    flaky = flaky_cases(runner)
    assert not any(f["app"] == "Settings" and f["case"] == "wifi_toggle" for f in flaky)
