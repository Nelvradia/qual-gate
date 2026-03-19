---
title: "Fix: Missing Unit Test Coverage"
status: current
last-updated: 2026-03-19
instrument: test-tomographe
severity-range: "Major"
---

# Fix: Missing Unit Test Coverage

## What this means

Your codebase has functions, methods, or modules with insufficient or zero unit test coverage.
Untested code is unverified code — any future change can silently break it with no safety net.
Coverage gaps accumulate technical debt: the longer code goes untested, the harder it becomes to
add tests because the code was never designed with testability in mind. The test-tomographe flags
this when coverage drops below your configured threshold or when newly added code lacks
corresponding tests.

## How to fix

### Python

**Measure coverage to identify gaps:**

```bash
# Install coverage tooling
pip install pytest-cov

# Run tests with coverage report
pytest tests/ --cov=src --cov-report=term-missing

# Generate HTML report for visual inspection
pytest tests/ --cov=src --cov-report=html

# Fail if below threshold
pytest tests/ --cov=src --cov-fail-under=80
```

**Write tests for uncovered code:**

```python
# src/calculator.py
def compound_interest(principal: float, rate: float, periods: int) -> float:
    if principal < 0 or rate < 0 or periods < 0:
        raise ValueError(f"All inputs must be non-negative: {principal=}, {rate=}, {periods=}")
    return principal * (1 + rate) ** periods

# tests/unit/test_calculator.py
import pytest
from src.calculator import compound_interest

def test_compound_interest_basic():
    result = compound_interest(1000.0, 0.05, 10)
    assert result == pytest.approx(1628.89, rel=1e-2), f"Expected ~1628.89, got {result}"

def test_compound_interest_zero_rate():
    assert compound_interest(1000.0, 0.0, 10) == 1000.0, "Zero rate should return principal"

@pytest.mark.parametrize("principal,rate,periods", [
    (-100.0, 0.05, 10),
    (100.0, -0.05, 10),
    (100.0, 0.05, -1),
])
def test_compound_interest_rejects_negative_inputs(principal, rate, periods):
    with pytest.raises(ValueError, match="non-negative"):
        compound_interest(principal, rate, periods)
```

### Rust

**Measure coverage with cargo-llvm-cov:**

```bash
cargo install cargo-llvm-cov
cargo llvm-cov --workspace                        # summary
cargo llvm-cov --workspace --html                  # HTML report
cargo llvm-cov --workspace --fail-under-lines 80   # CI gate
```

**Write tests for uncovered code:**

```rust
pub fn compound_interest(principal: f64, rate: f64, periods: u32) -> Result<f64, String> {
    if principal < 0.0 || rate < 0.0 {
        return Err(format!("Inputs must be non-negative: {principal}, {rate}"));
    }
    Ok(principal * (1.0 + rate).powi(periods as i32))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn compound_interest_basic() {
        let result = compound_interest(1000.0, 0.05, 10).unwrap();
        assert!((result - 1628.89).abs() < 1.0, "Expected ~1628.89, got {result}");
    }

    #[test]
    fn compound_interest_rejects_negative_principal() {
        assert!(compound_interest(-100.0, 0.05, 10).is_err());
    }
}
```

### TypeScript

**Measure coverage with c8 or Jest/Vitest:**

```bash
npx vitest run --coverage --coverage.thresholds.lines=80   # Vitest
npx jest --coverage --coverageThreshold='{"global":{"lines":80}}'  # Jest
```

**Write tests for uncovered code:**

```typescript
// tests/unit/calculator.test.ts
import { describe, it, expect } from "vitest";
import { compoundInterest } from "../../src/calculator";

describe("compoundInterest", () => {
  it("calculates correctly for standard inputs", () => {
    expect(compoundInterest(1000, 0.05, 10)).toBeCloseTo(1628.89, 1);
  });

  it("returns principal when rate is zero", () => {
    expect(compoundInterest(1000, 0.0, 10)).toBe(1000);
  });

  it.each([[-100, 0.05, 10], [100, -0.05, 10], [100, 0.05, -1]])(
    "rejects negative input (%d, %d, %d)", (p, r, n) => {
      expect(() => compoundInterest(p, r, n)).toThrow("non-negative");
    },
  );
});
```

### Go

**Measure coverage with go test:**

```bash
go test -cover ./...                            # summary
go test -coverprofile=coverage.out ./...        # profile
go tool cover -html=coverage.out -o coverage.html  # HTML report
go tool cover -func=coverage.out                # per-function breakdown
```

**Write tests for uncovered code:**

```go
func TestCompoundInterest_Basic(t *testing.T) {
    result, err := CompoundInterest(1000.0, 0.05, 10)
    if err != nil {
        t.Fatalf("unexpected error: %v", err)
    }
    if math.Abs(result-1628.89) > 1.0 {
        t.Errorf("expected ~1628.89, got %.2f", result)
    }
}

func TestCompoundInterest_RejectsNegative(t *testing.T) {
    cases := []struct{ name string; p, r float64; n int }{
        {"negative principal", -100, 0.05, 10},
        {"negative rate", 100, -0.05, 10},
        {"negative periods", 100, 0.05, -1},
    }
    for _, tc := range cases {
        t.Run(tc.name, func(t *testing.T) {
            _, err := CompoundInterest(tc.p, tc.r, tc.n)
            if err == nil {
                t.Error("expected error for negative input, got nil")
            }
        })
    }
}
```

### General

**Strategy for tackling coverage gaps:**

1. **Start with the coverage report.** Sort files by coverage ascending. Lowest files first.
2. **Prioritise by risk.** Business-critical code with zero coverage is more dangerous than a
   utility helper at 60%. Focus on money, auth, data persistence, safety-critical logic.
3. **Test behaviour, not lines.** Chasing 100% line coverage leads to brittle tests. Focus on
   meaningful assertions that verify behaviour, edge cases, and error paths.
4. **Untestable code is a design smell.** If a function is hard to test, it likely does too
   much, has hidden dependencies, or mixes I/O with logic. Refactor first, then test.
5. **Add tests incrementally.** Set a ratchet: coverage can only go up per MR. Increase the
   threshold by 1-2% per sprint.

## Prevention

**CI coverage gates (run on every MR):**

```yaml
# GitLab CI example
unit-tests:
  stage: test
  script:
    - pytest tests/unit/ --cov=src --cov-fail-under=80    # Python
    - cargo llvm-cov --workspace --fail-under-lines 80     # Rust
    - npx vitest run --coverage --coverage.thresholds.lines=80  # TypeScript
    - go test -cover ./...                                 # Go
  allow_failure: false
```

**Coverage ratchet in CI:**

- Store current coverage in a `coverage-baseline` file. Block merge if coverage drops.
- Use `diff-cover` (Python) to report coverage on changed lines only, preventing old untested
  code from blocking new MRs while enforcing coverage on new code.

**Code review checklist:**

- Does the MR include tests for all new public functions?
- Are error paths and edge cases covered?
- Is the coverage delta non-negative?
