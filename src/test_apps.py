"""Mock infotainment app interfaces — SIMULATED apps (Keyboard, Smartlight,
Global Search, Settings) that stand in for real infotainment software;
see README. Each app exposes a small set
of named test cases with realistic pass/fail/flaky behavior driven by a
seeded RNG, so there's genuine variance to detect and report on rather
than an always-green suite.
"""
import random


class TestResult:
    PASS = "PASS"
    FAIL = "FAIL"


class MockApp:
    """Base class for a simulated infotainment app under test."""

    name = "MockApp"
    test_cases = []

    def __init__(self, seed=None):
        self._rng = random.Random(seed)

    def run_case(self, case_id):
        if case_id not in self.test_cases:
            raise ValueError(f"Unknown test case '{case_id}' for {self.name}")
        outcome = self._case_outcome(case_id)
        return outcome

    def _case_outcome(self, case_id):
        raise NotImplementedError


class KeyboardApp(MockApp):
    name = "Keyboard"
    test_cases = ["layout_switch_de_en", "autocorrect_suggestion", "long_press_special_char", "voice_input_toggle"]

    def _case_outcome(self, case_id):
        # voice_input_toggle is seeded flaky (~30% fail rate) — models a
        # real intermittent bug worth flagging in a flaky-case report.
        if case_id == "voice_input_toggle":
            return TestResult.FAIL if self._rng.random() < 0.3 else TestResult.PASS
        return TestResult.PASS


class SmartlightApp(MockApp):
    name = "Smartlight"
    test_cases = ["ambient_color_sync", "brightness_ramp", "notification_pulse"]

    def _case_outcome(self, case_id):
        # brightness_ramp is a seeded deterministic failure (a known bug),
        # not flaky — models a genuine regression the suite should catch
        # every time, not just sometimes.
        if case_id == "brightness_ramp":
            return TestResult.FAIL
        return TestResult.PASS


class GlobalSearchApp(MockApp):
    name = "GlobalSearch"
    test_cases = ["search_contacts", "search_poi", "search_media", "search_settings_deep_link", "empty_query_handling"]

    def _case_outcome(self, case_id):
        if case_id == "search_poi":
            return TestResult.FAIL if self._rng.random() < 0.15 else TestResult.PASS
        return TestResult.PASS


class SettingsApp(MockApp):
    name = "Settings"
    test_cases = ["wifi_toggle", "display_theme_switch", "language_change", "factory_reset_confirmation_dialog"]

    def _case_outcome(self, case_id):
        return TestResult.PASS


ALL_APPS = {
    "Keyboard": KeyboardApp,
    "Smartlight": SmartlightApp,
    "GlobalSearch": GlobalSearchApp,
    "Settings": SettingsApp,
}
