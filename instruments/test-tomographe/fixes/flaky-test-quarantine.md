---
title: "Fix: Flaky Test Quarantine"
status: current
last-updated: 2026-03-19
instrument: test-tomographe
severity-range: "Major"
---

# Fix: Flaky Test Quarantine

## What this means

A flaky test is one that passes and fails non-deterministically without any code change. Flaky
tests erode trust in the test suite: developers start ignoring failures ("it's probably just that
flaky test again"), retrying pipelines until they go green, and eventually disabling CI gates
entirely. The test-tomographe flags tests that show intermittent pass/fail patterns across recent
pipeline runs or that have been manually skipped without a tracking issue. Every flaky test must
be quarantined immediately (skipped with a linked issue), diagnosed, and fixed within a bounded
timeframe.

## How to fix

### Python

**Quarantine a flaky test with a tracking issue:**

```python
# tests/unit/test_scheduler.py
import pytest

@pytest.mark.skip(reason="FLAKY: #247 — intermittent timeout in CI, passes locally")
def test_scheduler_dispatches_within_deadline():
    """This test fails ~10% of the time in CI due to timing sensitivity."""
    ...
```

**Use pytest-rerunfailures to confirm flakiness before quarantining:**

```bash
# Install the plugin
pip install pytest-rerunfailures

# Re-run failed tests up to 3 times to distinguish flaky from broken
pytest tests/ --reruns 3 --reruns-delay 1

# Only re-run tests marked as potentially flaky
pytest tests/ -m "flaky" --reruns 3
```

**Diagnose timing-related flakiness:**

```python
# BAD: depends on wall-clock timing
def test_cache_expires():
    cache.set("key", "value", ttl_seconds=1)
    time.sleep(1.1)  # fragile — CI machines may be slow
    assert cache.get("key") is None

# GOOD: use freezegun or a clock abstraction
from freezegun import freeze_time

def test_cache_expires():
    with freeze_time("2026-01-01 12:00:00") as frozen:
        cache.set("key", "value", ttl_seconds=60)
        frozen.move_to("2026-01-01 12:01:01")
        assert cache.get("key") is None, "Cache entry should expire after TTL"
```

**Diagnose shared-state flakiness:**

```python
# BAD: tests share a module-level list, order-dependent
_events = []

def test_add_event():
    _events.append("click")
    assert len(_events) == 1  # fails if another test ran first

# GOOD: use fixtures for isolation
@pytest.fixture
def events():
    return []

def test_add_event(events):
    events.append("click")
    assert len(events) == 1
```

### Rust

**Quarantine a flaky test:**

```rust
#[test]
#[ignore = "FLAKY: #247 — race condition in async task scheduling"]
fn test_task_scheduler_fairness() {
    // This test intermittently fails when CI runners are under load.
    // Root cause investigation tracked in issue #247.
}
```

**Run quarantined tests separately to monitor them:**

```bash
# Run only ignored (quarantined) tests
cargo test -- --ignored

# Run all tests including ignored
cargo test -- --include-ignored
```

**Fix non-deterministic async tests:**

```rust
// BAD: depends on real time
#[tokio::test]
async fn test_timeout_fires() {
    let start = Instant::now();
    do_work_with_timeout(Duration::from_millis(100)).await;
    assert!(start.elapsed() >= Duration::from_millis(100)); // fragile
}

// GOOD: use tokio::time::pause for deterministic time
#[tokio::test(start_paused = true)]
async fn test_timeout_fires() {
    let result = tokio::time::timeout(
        Duration::from_millis(100),
        futures::future::pending::<()>(),
    ).await;
    assert!(result.is_err(), "Timeout should fire");
}
```

### TypeScript

**Quarantine a flaky test:**

```typescript
// tests/unit/scheduler.test.ts
describe("TaskScheduler", () => {
  it.skip("dispatches within deadline — FLAKY #247", () => {
    // Intermittent failure due to setTimeout precision in CI.
    // Tracked in issue #247.
  });
});
```

**Use fake timers to eliminate timing flakiness:**

```typescript
// BAD: real timers
it("debounces rapid calls", async () => {
  const fn = debounce(callback, 200);
  fn();
  fn();
  fn();
  await new Promise((r) => setTimeout(r, 250)); // fragile
  expect(callback).toHaveBeenCalledTimes(1);
});

// GOOD: fake timers
it("debounces rapid calls", () => {
  vi.useFakeTimers();
  const fn = debounce(callback, 200);
  fn();
  fn();
  fn();
  vi.advanceTimersByTime(200);
  expect(callback).toHaveBeenCalledTimes(1);
  vi.useRealTimers();
});
```

### Go

**Quarantine a flaky test:**

```go
func TestSchedulerFairness(t *testing.T) {
    t.Skip("FLAKY: #247 — race condition under CI load, investigating")
    // ... test body ...
}
```

**Detect race conditions causing flakiness:**

```bash
# Run tests with the race detector
go test -race -count=5 ./...

# The -count flag runs each test multiple times to surface intermittent failures
go test -count=10 -timeout=120s ./...
```

**Fix shared-state flakiness:**

```go
// BAD: package-level variable shared between tests
var counter int

func TestIncrement(t *testing.T) {
    counter++
    if counter != 1 { // fails depending on test execution order
        t.Errorf("expected 1, got %d", counter)
    }
}

// GOOD: test-local state
func TestIncrement(t *testing.T) {
    counter := 0
    counter++
    if counter != 1 {
        t.Errorf("expected 1, got %d", counter)
    }
}
```

### General

**Root cause patterns for flaky tests (ordered by frequency):**

1. **Timing dependencies.** Tests use `sleep()`, real clocks, or wall-time assertions. Fix by
   using fake/frozen time or event-based synchronisation.
2. **Shared mutable state.** Tests read/write a shared variable, database table, or file.
   Earlier tests leave residue that later tests depend on or conflict with. Fix by isolating
   state per test (fixtures, transactions, temp directories).
3. **External service dependencies.** Tests call a real API, DNS, or network service that is
   intermittently unavailable. Fix by using testcontainers, mocks, or recorded responses.
4. **Test ordering.** Test A sets up state that Test B implicitly relies on. Works when run
   together but fails when run individually or in different order. Fix by making every test
   self-contained.
5. **Resource exhaustion.** Tests leak file handles, connections, or goroutines. Under CI load,
   the system runs out of resources. Fix by using cleanup/teardown hooks and connection pools.
6. **Non-deterministic iteration.** Iterating over hash maps or sets and asserting on order.
   Fix by sorting before comparison or using order-independent assertions.

**Quarantine workflow:**

1. **Detect:** CI shows a test failure that passes on retry without code changes.
2. **Quarantine immediately:** Skip the test with a reason string referencing an issue ID.
3. **File a tracking issue:** Include the failure log, frequency estimate, and suspected root
   cause category from the list above.
4. **Set a deadline:** Flaky tests quarantined for more than 2 weeks get a dedicated fix session.
5. **Fix and restore:** Address the root cause, verify with repeated runs (`--count=10` or
   equivalent), then remove the skip annotation.

## Prevention

**CI flake detection:**

```yaml
# GitLab CI: re-run failures to detect flakes
unit-tests:
  stage: test
  script:
    - pytest tests/unit/ -v --reruns 2
  retry:
    max: 1
    when: script_failure
```

**Track flaky test metrics:**

- Log every test retry in CI. If a test is retried more than twice in a week, auto-file an issue.
- Maintain a flaky test dashboard or label in your issue tracker.
- Review quarantined tests weekly. Tests quarantined longer than 2 sprints should be either fixed
  or deleted (if the behaviour is no longer relevant).

**Code review checklist:**

- Does the test use `sleep()` or real time? Suggest fake timers.
- Does the test depend on global/shared state? Suggest fixtures or per-test setup.
- Does the test assert on iteration order of unordered collections?
- Does the test hit a real external service without a fallback?
