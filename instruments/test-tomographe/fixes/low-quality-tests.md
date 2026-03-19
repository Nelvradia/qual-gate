---
title: "Fix: Low-Quality Tests"
status: current
last-updated: 2026-03-19
instrument: test-tomographe
severity-range: "Minor–Major"
---

# Fix: Low-Quality Tests

## What this means

Your test suite contains tests that provide false confidence: they run, they pass, but they do
not meaningfully verify behaviour. Common symptoms include tests with no assertions, tests that
assert on implementation details instead of outcomes, over-mocked tests that only verify mock
wiring, poor naming that makes failures undiagnosable, and missing assertion messages. These
tests inflate coverage numbers while providing little actual safety.

## How to fix

### Python

**No-assertion tests — add meaningful assertions:**

```python
# BAD: runs the function but asserts nothing
def test_process_order():
    result = process_order(order_id=42)

# GOOD: assert on the outcome
def test_process_order_returns_confirmation():
    result = process_order(order_id=42)
    assert result.status == "confirmed", f"Expected 'confirmed', got '{result.status}'"
    assert result.order_id == 42, f"Expected order_id 42, got {result.order_id}"
```

**Over-mocking — test behaviour, not wiring:**

```python
# BAD: mocks everything, tests nothing real
def test_send_notification(mocker):
    mock_client = mocker.patch("src.notifier.EmailClient")
    mock_client.return_value.send.return_value = True
    send_notification(user_id=1, event="signup")
    mock_client.return_value.send.assert_called_once()  # only tests mock wiring

# GOOD: mock only the boundary, assert on meaningful output
def test_send_notification_formats_email_correctly(mocker):
    mock_client = mocker.patch("src.notifier.EmailClient")
    captured = []
    mock_client.return_value.send.side_effect = lambda msg: captured.append(msg)
    send_notification(user_id=1, event="signup")
    assert len(captured) == 1, "Expected exactly one email to be sent"
    assert "Welcome" in captured[0].subject, f"Wrong subject: {captured[0].subject}"
```

**Naming — use `test_<unit>_<behaviour>_<condition>`:**

```python
# BAD                                    # GOOD
def test_1(): ...                        def test_discount_applies_bulk_rate_above_100(): ...
def test_calc(): ...                     def test_discount_rejects_negative_quantity(): ...
```

### Rust

**No-assertion tests:**

```rust
// BAD: compiles and runs but proves nothing
#[test]
fn test_parse_config() {
    let _ = parse_config("config.toml");
}

// GOOD: assert on the parsed result
#[test]
fn parse_config_reads_all_required_fields() {
    let config = parse_config("fixtures/valid-config.toml")
        .expect("Valid config should parse without error");
    assert_eq!(config.port, 8080, "Default port should be 8080");
    assert!(config.workers > 0, "Worker count must be positive, got {}", config.workers);
}
```

**Over-mocking — capture and inspect saved data instead of verifying call counts:**

```rust
// BAD: mock verifies call count, not behaviour
#[test]
fn test_order_processor() {
    let mut mock_db = MockDatabase::new();
    mock_db.expect_save().times(1).returning(|_| Ok(()));
    let processor = OrderProcessor::new(Box::new(mock_db));
    processor.process(Order::new(42)).unwrap();
}

// GOOD: capture and inspect the saved data
#[test]
fn order_processor_saves_with_correct_status() {
    let saved = Arc::new(Mutex::new(Vec::new()));
    let saved_clone = saved.clone();
    let mut mock_db = MockDatabase::new();
    mock_db.expect_save().returning(move |order| {
        saved_clone.lock().unwrap().push(order.clone());
        Ok(())
    });
    let processor = OrderProcessor::new(Box::new(mock_db));
    processor.process(Order::new(42)).unwrap();
    let orders = saved.lock().unwrap();
    assert_eq!(orders[0].status, OrderStatus::Processed);
}
```

### TypeScript

**No-assertion tests:**

```typescript
// BAD: test body has no expect()
it("processes the order", () => {
  const result = processOrder({ id: 42, items: ["widget"] });
});

// GOOD: assert on the result
it("processes order and returns confirmation with correct ID", () => {
  const result = processOrder({ id: 42, items: ["widget"] });
  expect(result.status).toBe("confirmed");
  expect(result.orderId).toBe(42);
});
```

**Improve test organisation:**

```typescript
// BAD: flat, unnamed tests
test("test1", () => { ... });

// GOOD: grouped by behaviour with descriptive names
describe("DiscountCalculator", () => {
  describe("when quantity exceeds bulk threshold", () => {
    it("applies 15% bulk discount", () => { ... });
    it("caps discount at maximum allowed value", () => { ... });
  });
});
```

### Go

**No-assertion tests — use table-driven tests with clear names:**

```go
// BAD: calls the function, ignores errors, asserts nothing
func TestParseConfig(t *testing.T) {
    ParseConfig("config.toml")
}

// GOOD: table-driven with descriptive names
func TestCalculateDiscount(t *testing.T) {
    cases := []struct {
        name     string
        qty      int
        tier     string
        expected float64
    }{
        {"single item no discount", 1, "none", 0.0},
        {"bulk quantity gets 15%", 150, "none", 0.15},
        {"loyalty tier adds 5%", 1, "gold", 0.05},
    }
    for _, tc := range cases {
        t.Run(tc.name, func(t *testing.T) {
            got := CalculateDiscount(tc.qty, tc.tier)
            if got != tc.expected {
                t.Errorf("CalculateDiscount(%d, %q) = %.2f, want %.2f",
                    tc.qty, tc.tier, got, tc.expected)
            }
        })
    }
}
```

### General

**Common low-quality test patterns:**

| Pattern | Problem | Fix |
|---|---|---|
| No assertions | Test passes vacuously | Add assertions on return values |
| Assert only `!= nil` | Proves existence, not correctness | Assert on specific fields |
| Exact string matching | Breaks on formatting changes | Assert on semantic properties |
| Mock everything | Tests only mock wiring | Mock only external boundaries |
| Identical test bodies | Copy-paste with one value changed | Use parametrised tests |
| Test name is `test_1` | No diagnostic information on failure | `test_<unit>_<behaviour>_<condition>` |
| No failure message | CI says `AssertionError` with no context | Include expected vs actual |

**Refactoring test quality incrementally:**

1. **No-assertion tests first.** Search for test functions lacking `assert`/`expect`. Zero value.
2. **Add assertion messages.** Pays off immediately the next time a test fails in CI.
3. **Rename unclear tests.** `test_it_works` becomes
   `test_parser_handles_empty_input_gracefully`. Good names are documentation.
4. **Reduce over-mocking.** For each mock, ask: "Does this enforce the same contract as the real
   dependency?" If not, the test is testing fiction.

## Prevention

**Lint rules to catch low-quality tests:**

```yaml
# Python: ruff.toml
[lint]
select = ["PT"]  # pytest-style rules including PT009

# TypeScript: .eslintrc.json
{ "rules": { "jest/expect-expect": "error", "jest/valid-title": "error" } }
```

**Code review checklist:**

- Does every test have at least one meaningful assertion?
- Do assertions include failure messages with context?
- Are test names descriptive enough to diagnose failures without reading the test body?
- Are mocks limited to external boundaries (not internal implementation)?

**Mutation testing (advanced):** Modify source code and check whether tests catch the change.

```bash
mutmut run --paths-to-mutate=src/       # Python
cargo mutants                            # Rust
npx stryker run                          # TypeScript
go-mutesting ./...                       # Go
```
