"""Orchestrates: check out a rig, run a suite of test cases against a
chosen (simulated) app, log structured results, release the rig. Models
"Durchführung und Dokumentation von Tests" plus "Automatisierung von
Test- und Validierungsprozessen" from the posting.
"""
import time
from dataclasses import dataclass, field

from rig_pool import RigPool, RigCheckoutError
from test_apps import ALL_APPS, TestResult


@dataclass
class TestRunRecord:
    rig_id: str
    app_name: str
    case_id: str
    result: str
    user: str
    duration_ms: float
    timestamp: float


class TestRunner:
    def __init__(self, pool: RigPool):
        self.pool = pool
        self.history = []

    def run_suite(self, user, app_name, case_ids=None, timestamp_fn=time.perf_counter, app_seed=None):
        """Checks out a rig for `user`, runs each requested test case
        (defaults to the app's full case list) against a simulated
        instance of `app_name`, logs every result, then releases the rig.

        Returns (rig_id_used, list[TestRunRecord]) — rig_id_used is None
        if the user was queued instead of served immediately (no tests
        run in that call; caller should retry once notified).

        timestamp_fn is injectable so tests can pass a deterministic clock
        instead of depending on wall-clock time.
        """
        if app_name not in ALL_APPS:
            raise ValueError(f"Unknown app '{app_name}'")

        rig_id = self.pool.checkout(user)
        if rig_id is None:
            return None, []  # queued — caller must wait/retry

        self.pool.begin_use(rig_id, user)

        app = ALL_APPS[app_name](seed=app_seed)
        cases = case_ids if case_ids is not None else list(app.test_cases)

        records = []
        for case_id in cases:
            start = timestamp_fn()
            result = app.run_case(case_id)
            end = timestamp_fn()
            record = TestRunRecord(
                rig_id=rig_id,
                app_name=app_name,
                case_id=case_id,
                result=result,
                user=user,
                duration_ms=(end - start) * 1000,
                timestamp=end,
            )
            records.append(record)
            self.history.append(record)

        self.pool.release(rig_id, user)
        return rig_id, records
