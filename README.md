# Remote Test-Rig Access & Test-Execution Tool

A real, tested Python tool built to close a specific gap for CARIAD's
"Working Student — Infotainment Apps Testing & Tooling" posting, which
centers on developing/maintaining remote-access tools for shared
infotainment test setups, running and documenting tests for specific apps
(Keyboard, Smartlight, Global Search, Settings), and automating test/
validation processes.

## What this is (read before citing anywhere)

**There is no real infotainment hardware or software here.** I have no
access to CARIAD's test rigs, in-vehicle infotainment systems, or the real
Keyboard/Smartlight/Global Search/Settings applications. Building or
claiming experience against real hardware I don't have would be dishonest,
so instead I built the closest thing I could actually construct and verify:

- **Simulated test rigs** — a pool of in-memory rig objects standing in
  for shared hardware test setups, with the same operational lifecycle a
  real one would have (free → reserved → in use → released, or flagged
  faulty and pulled from the pool).
- **Simulated infotainment apps** — four mock app interfaces named after
  the posting's own examples (Keyboard, Smartlight, Global Search,
  Settings), each with deterministic-but-imperfect behavior (some test
  cases are seeded to fail or flake) so there's real pass/fail variance to
  detect and report on, not a trivial always-green suite.

If asked in an interview: I have not worked with real infotainment
hardware or CARIAD's actual test infrastructure. This project demonstrates
the same underlying skills the posting asks for — remote-access/session
tooling, test-environment health monitoring and fault handling, running
and documenting structured test cases, and automating the whole flow —
built and verified against a simulated environment because a real one
wasn't available to me.

## What this models, and how it maps to the posting

- **`src/rig_pool.py`** — a pool of shared test rigs with status tracking
  (`FREE`, `RESERVED`, `IN_USE`, `MAINTENANCE`, `FAULTY`) and a checkout/
  release lifecycle with FIFO queueing when every rig is busy — the direct
  equivalent of "Tools für den Remote-Zugriff auf Testaufbauten," where
  multiple developers/testers share a limited pool of physical rigs.
- **`src/health.py`** — periodic simulated health checks per rig, with a
  seeded failure rate; rigs that fail enough consecutive checks are
  automatically pulled into `FAULTY` and quarantined from the available
  pool until manually reset — models "Betrieb, Wartung und Fehleranalyse
  von Testumgebungen."
- **`src/test_apps.py`** — four mock app interfaces (Keyboard, Smartlight,
  Global Search, Settings), each exposing a small set of named test cases
  with realistic pass/fail/flaky behavior — models "Durchführung ... von
  Tests für Anwendungen wie Keyboard, Smartlight, Global Search und
  Settings."
- **`src/test_runner.py`** — checks out a rig, runs a requested suite of
  test cases against a chosen app, records structured results (rig, app,
  case, result, duration, timestamp), and releases the rig afterward —
  models "Durchführung und Dokumentation von Tests" plus "Automatisierung
  von Test- und Validierungsprozessen."
- **`src/reporting.py`** — pool status (free/in-use/faulty/queue depth),
  and a test-run history report (pass rate by app, flaky-case detection
  across repeated runs) — the kind of at-a-glance operational view a
  remote-access tool would need to surface.

## Verification

26 automated tests (`tests/test_rig_tool.py`) covering: checkout/release
lifecycle and FIFO queue ordering, health-check-driven fault detection and
quarantine (and that a quarantined rig is never handed out, and that a rig
currently in use isn't yanked away by a health-check failure alone), each
mock app's test-case behavior (deterministic pass, deterministic fail, and
flaky), end-to-end test-run logging correctness, and the reporting
functions against known expected output.

## Running it

```bash
python3 src/demo.py           # walks through a realistic session: checkout, run tests, a rig going faulty, queueing, reporting
python3 -m pytest tests/ -v   # runs all 23 tests
```
