# Remote Test-Rig Access & Test-Execution Tool

A tested Python tool for remote access to shared infotainment test setups,
for running and documenting tests for specific apps (Keyboard, Smartlight,
Global Search, Settings), and for automating test and validation processes.

## What it does

It combines remote-access and session tooling, test-environment health
monitoring and fault handling, structured test-case execution and
documentation, and automation of the whole flow.

## Scope

The rigs and apps are simulated, and the tool is built and verified against
that simulated environment:

- **Simulated test rigs** — a pool of in-memory rig objects standing in
  for shared hardware test setups, with the same operational lifecycle a
  real one would have (free → reserved → in use → released, or flagged
  faulty and pulled from the pool).
- **Simulated infotainment apps** — four mock app interfaces (Keyboard,
  Smartlight, Global Search, Settings), each with deterministic-but-
  imperfect behavior (some test cases are seeded to fail or flake) so
  there is real pass/fail variance to detect and report on, not a trivial
  always-green suite.

The health checks and app interfaces are pluggable, so real hardware and
software can replace the simulations.

## Project structure

- **`src/rig_pool.py`** — a pool of shared test rigs with status tracking
  (`FREE`, `RESERVED`, `IN_USE`, `MAINTENANCE`, `FAULTY`) and a checkout/
  release lifecycle with FIFO queueing when every rig is busy, so multiple
  developers and testers can share a limited pool of rigs.
- **`src/health.py`** — periodic simulated health checks per rig, with a
  seeded failure rate; rigs that fail enough consecutive checks are
  automatically pulled into `FAULTY` and quarantined from the available
  pool until manually reset. This covers operation, maintenance, and fault
  analysis of test environments.
- **`src/test_apps.py`** — four mock app interfaces (Keyboard, Smartlight,
  Global Search, Settings), each exposing a small set of named test cases
  with realistic pass/fail/flaky behavior.
- **`src/test_runner.py`** — checks out a rig, runs a requested suite of
  test cases against a chosen app, records structured results (rig, app,
  case, result, duration, timestamp), and releases the rig afterward,
  automating test execution and documentation.
- **`src/reporting.py`** — pool status (free/in-use/faulty/queue depth),
  and a test-run history report (pass rate by app, flaky-case detection
  across repeated runs): the at-a-glance operational view a remote-access
  tool needs to surface.

## Tests

26 automated tests (`tests/test_rig_tool.py`) covering: checkout/release
lifecycle and FIFO queue ordering, health-check-driven fault detection and
quarantine (a quarantined rig is never handed out, and a rig currently in
use isn't yanked away by a health-check failure alone), each mock app's
test-case behavior (deterministic pass, deterministic fail, and flaky),
end-to-end test-run logging correctness, and the reporting functions
against known expected output.

## Running it

```bash
python3 src/demo.py           # walks through a realistic session: checkout, run tests, a rig going faulty, queueing, reporting
python3 -m pytest tests/ -v   # runs all 26 tests
```
