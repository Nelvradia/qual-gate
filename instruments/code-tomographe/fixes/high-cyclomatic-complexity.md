---
title: "Fix: High Cyclomatic Complexity"
status: current
last-updated: 2026-03-19
instrument: code-tomographe
severity-range: "Minor--Major"
---

# Fix: High Cyclomatic Complexity

## What this means

Cyclomatic complexity measures the number of independent execution paths through a function.
A function with complexity 15 has 15 distinct paths, meaning it needs at least 15 test cases
for full branch coverage. High complexity correlates strongly with defect density: functions
above complexity 10 are harder to understand, test, review, and modify safely. Functions between
50 and 100 lines are Minor; above 100 lines or with nesting deeper than 5 levels are Major.

## How to fix

### Python

**Measurement:**

```bash
# radon: grades A (1-5) through F (41+)
pip install radon
radon cc src/ -s -n C    # show only C grade and worse (complexity >= 11)
```

**Pattern 1 -- Early return (guard clauses):**

```python
# BAD: nested conditionals, complexity 5
def process_order(order: Order) -> Result:
    if order is not None:
        if order.is_valid():
            if order.has_stock():
                return fulfill(order)
            else:
                return Result.out_of_stock()
        else:
            return Result.invalid()
    else:
        return Result.missing()

# GOOD: guard clauses, complexity 4, flat structure
def process_order(order: Order) -> Result:
    if order is None:
        return Result.missing()
    if not order.is_valid():
        return Result.invalid()
    if not order.has_stock():
        return Result.out_of_stock()
    return fulfill(order)
```

**Pattern 2 -- Extract method:**

```python
# BAD: one function doing validation + transformation + persistence
def handle_submission(data: dict) -> Response:
    # 30 lines of validation ...
    # 20 lines of transformation ...
    # 15 lines of database writes ...
    pass

# GOOD: each concern in its own function
def handle_submission(data: dict) -> Response:
    errors = validate_submission(data)
    if errors:
        return Response.bad_request(errors)
    record = transform_to_record(data)
    save_record(record)
    return Response.created(record.id)
```

**Pattern 3 -- Table-driven logic:**

```python
# BAD: long if/elif chain
def get_status_label(code: int) -> str:
    if code == 0:
        return "pending"
    elif code == 1:
        return "active"
    elif code == 2:
        return "suspended"
    elif code == 3:
        return "closed"
    else:
        return "unknown"

# GOOD: lookup table
_STATUS_LABELS: dict[int, str] = {
    0: "pending",
    1: "active",
    2: "suspended",
    3: "closed",
}

def get_status_label(code: int) -> str:
    return _STATUS_LABELS.get(code, "unknown")
```

### Rust

**Measurement:**

```bash
# clippy reports cognitive complexity above the configured threshold
cargo clippy -- -W clippy::cognitive_complexity
```

**Pattern 1 -- Guard clauses with early return:**

```rust
// BAD: deeply nested
fn process(input: Option<&str>) -> Result<Output, Error> {
    if let Some(val) = input {
        if !val.is_empty() {
            if let Ok(parsed) = val.parse::<u32>() {
                return Ok(Output::new(parsed));
            }
        }
    }
    Err(Error::InvalidInput)
}

// GOOD: flat with early returns
fn process(input: Option<&str>) -> Result<Output, Error> {
    let val = input.ok_or(Error::InvalidInput)?;
    if val.is_empty() {
        return Err(Error::InvalidInput);
    }
    let parsed: u32 = val.parse().map_err(|_| Error::InvalidInput)?;
    Ok(Output::new(parsed))
}
```

**Pattern 2 -- Strategy pattern via enum dispatch:**

```rust
// BAD: match with complex logic in each arm
fn execute(action: Action, ctx: &mut Context) -> Result<()> {
    match action {
        Action::Create => { /* 20 lines */ }
        Action::Update => { /* 25 lines */ }
        Action::Delete => { /* 15 lines */ }
    }
}

// GOOD: delegate to methods
impl Action {
    fn execute(&self, ctx: &mut Context) -> Result<()> {
        match self {
            Self::Create => self.handle_create(ctx),
            Self::Update => self.handle_update(ctx),
            Self::Delete => self.handle_delete(ctx),
        }
    }
}
```

### TypeScript

**Measurement:**

```bash
npx eslint --rule '{"complexity": ["warn", 10]}' src/
```

**Pattern -- Replace conditional chains with polymorphism:**

```typescript
// BAD: switch on type string
function calculatePrice(item: Item): number {
  switch (item.type) {
    case 'book': return item.basePrice * 0.9;
    case 'electronics': return item.basePrice * 1.2;
    case 'food': return item.basePrice;
    default: throw new Error(`Unknown type: ${item.type}`);
  }
}

// GOOD: strategy map
const pricingStrategies: Record<string, (base: number) => number> = {
  book: (base) => base * 0.9,
  electronics: (base) => base * 1.2,
  food: (base) => base,
};

function calculatePrice(item: Item): number {
  const strategy = pricingStrategies[item.type];
  if (!strategy) throw new Error(`Unknown type: ${item.type}`);
  return strategy(item.basePrice);
}
```

### Go

**Measurement:**

```bash
go install github.com/fzipp/gocyclo/cmd/gocyclo@latest
gocyclo -over 10 .
```

**Pattern -- Table-driven logic (idiomatic Go):**

```go
// BAD: long switch
func statusText(code int) string {
    switch code {
    case 200: return "OK"
    case 201: return "Created"
    case 400: return "Bad Request"
    case 404: return "Not Found"
    case 500: return "Internal Server Error"
    default:  return "Unknown"
    }
}

// GOOD: map lookup
var statusTexts = map[int]string{
    200: "OK",
    201: "Created",
    400: "Bad Request",
    404: "Not Found",
    500: "Internal Server Error",
}

func statusText(code int) string {
    if text, ok := statusTexts[code]; ok {
        return text
    }
    return "Unknown"
}
```

### General

**Refactoring decision tree:**

1. **Can you add guard clauses?** Invert conditions and return early to flatten nesting.
2. **Can you extract a helper?** If a block of code has a clear single purpose, extract it.
3. **Is there a lookup table?** Replace if/elif/switch chains that map input to output.
4. **Is there a strategy pattern?** Replace conditional behaviour selection with dispatch.
5. **Are you mixing concerns?** Split validation, transformation, and side effects.

**Thresholds (from config.yaml):**

| Metric | Soft limit | Hard limit | Severity |
|---|---|---|---|
| Function length | 50 lines | 100 lines | Minor / Major |
| File length | 300 lines | 800 lines | Minor / Major |
| Nesting depth | 4 levels | 5 levels | -- / Minor |

## Prevention

- Set complexity thresholds in your linter config so new violations fail CI.
- Code review checklist: "Does any new function exceed complexity 10?"
- Pair refactoring sessions for legacy hotspots -- timebox to 2 hours per function.
- Track complexity trends over time with periodic `radon` / `gocyclo` reports.
