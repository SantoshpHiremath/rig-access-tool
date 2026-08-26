"""Reporting functions over pool state and test-run history — the kind of
at-a-glance operational view a remote-access/test-tooling dashboard would
need to surface.
"""
from collections import defaultdict

from rig_pool import RigPool, RigStatus
from test_runner import TestRunner
from test_apps import TestResult


def pool_status_report(pool: RigPool):
    counts = pool.status_counts()
    return {
        "free": counts[RigStatus.FREE],
        "reserved": counts[RigStatus.RESERVED],
        "in_use": counts[RigStatus.IN_USE],
        "maintenance": counts[RigStatus.MAINTENANCE],
        "faulty": counts[RigStatus.FAULTY],
        "queue_depth": pool.queue_depth(),
    }


def pass_rate_by_app(runner: TestRunner):
    totals = defaultdict(lambda: {"pass": 0, "fail": 0})
    for record in runner.history:
        key = "pass" if record.result == TestResult.PASS else "fail"
        totals[record.app_name][key] += 1

    report = {}
    for app_name, counts in totals.items():
        total = counts["pass"] + counts["fail"]
        report[app_name] = {
            "pass": counts["pass"],
            "fail": counts["fail"],
            "pass_rate_pct": round(counts["pass"] / total * 100, 1) if total else None,
        }
    return report


def flaky_cases(runner: TestRunner, min_runs=2):
    """A test case is 'flaky' here if, across at least min_runs recorded
    executions, it produced BOTH a PASS and a FAIL at some point — i.e.
    its outcome isn't consistent. This is exactly the kind of signal a
    real test-tooling report needs to surface so a flaky case doesn't get
    silently trusted or silently ignored."""
    outcomes_by_case = defaultdict(set)
    counts_by_case = defaultdict(int)
    for record in runner.history:
        key = (record.app_name, record.case_id)
        outcomes_by_case[key].add(record.result)
        counts_by_case[key] += 1

    flaky = []
    for key, outcomes in outcomes_by_case.items():
        if counts_by_case[key] >= min_runs and len(outcomes) > 1:
            flaky.append({"app": key[0], "case": key[1], "runs": counts_by_case[key]})
    return flaky


def print_reports(pool: RigPool, runner: TestRunner):
    print("=== Pool Status ===")
    for k, v in pool_status_report(pool).items():
        print(f"  {k}: {v}")

    print("\n=== Pass Rate by App ===")
    for app_name, stats in pass_rate_by_app(runner).items():
        print(f"  {app_name}: {stats['pass']} pass / {stats['fail']} fail ({stats['pass_rate_pct']}%)")

    print("\n=== Flaky Cases Detected ===")
    flaky = flaky_cases(runner)
    if not flaky:
        print("  none")
    for f in flaky:
        print(f"  {f['app']}.{f['case']} — inconsistent across {f['runs']} runs")
