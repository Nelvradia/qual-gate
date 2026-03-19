---
title: "Fix: Code Duplication"
status: current
last-updated: 2026-03-19
instrument: code-tomographe
severity-range: "Minor--Major"
---

# Fix: Code Duplication

## What this means

Code duplication occurs when structurally identical or near-identical blocks appear in multiple
locations. When a bug is found in duplicated logic, every copy must be found and fixed -- and
missed copies become latent defects. Three or more identical blocks of 10+ lines each is Minor.
Systematic duplication across modules (e.g., every handler repeats the same validation or error
handling pattern) is Major because it indicates a missing abstraction. Not all duplication is
bad: sometimes two pieces of code look similar today but will diverge tomorrow. The key question
is whether the duplicated code changes for the same reason -- if yes, extract it.

## How to fix

### Python

**Detection:**

```bash
pip install jscpd
jscpd --min-lines 10 --reporters console src/
```

**Pattern 1 -- Extract shared function:**

```python
# BAD: duplicated validation in two handlers
def create_user(data: dict) -> Response:
    if not data.get("email"):
        return Response.bad_request("email required")
    if not data.get("name"):
        return Response.bad_request("name required")
    # ... create logic

def update_user(user_id: int, data: dict) -> Response:
    if not data.get("email"):
        return Response.bad_request("email required")
    if not data.get("name"):
        return Response.bad_request("name required")
    # ... update logic

# GOOD: extract validation
def _validate_user_fields(data: dict) -> list[str]:
    errors = []
    if not data.get("email"):
        errors.append("email required")
    if not data.get("name"):
        errors.append("name required")
    return errors

def create_user(data: dict) -> Response:
    if errors := _validate_user_fields(data):
        return Response.bad_request(errors)
    # ... create logic
```

**Pattern 2 -- Protocol / abstract base class:**

```python
from abc import ABC, abstractmethod

# BAD: each exporter duplicates file-handling boilerplate
class CsvExporter:
    def export(self, data, path):
        with open(path, "w") as f:
            # write header ... write rows ...
            pass

class JsonExporter:
    def export(self, data, path):
        with open(path, "w") as f:
            # serialize ... write ...
            pass

# GOOD: base class handles the shared concern
class Exporter(ABC):
    def export(self, data: list[dict], path: str) -> None:
        with open(path, "w") as f:
            self._write(data, f)

    @abstractmethod
    def _write(self, data: list[dict], f) -> None: ...
```

**Pattern 3 -- Parametric deduplication:**

```python
# BAD: three nearly identical test functions
def test_parse_csv(): ...
def test_parse_json(): ...
def test_parse_xml(): ...

# GOOD: parametrise
@pytest.mark.parametrize("fmt,input_file,expected", [
    ("csv", "data/sample.csv", EXPECTED_CSV),
    ("json", "data/sample.json", EXPECTED_JSON),
    ("xml", "data/sample.xml", EXPECTED_XML),
])
def test_parse(fmt, input_file, expected):
    result = parse(fmt, input_file)
    assert result == expected, f"Failed for format {fmt}"
```

### Rust

**Detection:**

```bash
# jscpd works across languages
jscpd --min-lines 10 --reporters console src/

# cargo-clone-detection (if available)
cargo install cargo-clone-detection
cargo clone-detection
```

**Pattern 1 -- Extract into a shared function:**

```rust
// BAD: repeated error mapping in multiple handlers
fn get_user(id: u32) -> Result<User, AppError> {
    let row = db::query("SELECT * FROM users WHERE id = ?", &[&id])
        .map_err(|e| AppError::Database(e.to_string()))?;
    // ...
}

fn get_order(id: u32) -> Result<Order, AppError> {
    let row = db::query("SELECT * FROM orders WHERE id = ?", &[&id])
        .map_err(|e| AppError::Database(e.to_string()))?;
    // ...
}

// GOOD: shared query helper
fn query_single(sql: &str, params: &[&dyn ToSql]) -> Result<Row, AppError> {
    db::query(sql, params).map_err(|e| AppError::Database(e.to_string()))
}
```

**Pattern 2 -- Trait-based abstraction:**

```rust
// BAD: each resource type duplicates CRUD boilerplate

// GOOD: define a trait for the shared behaviour
trait Repository {
    type Entity;
    type Id;

    fn table_name(&self) -> &str;

    fn find_by_id(&self, id: Self::Id) -> Result<Self::Entity, AppError> {
        let sql = format!("SELECT * FROM {} WHERE id = ?", self.table_name());
        let row = query_single(&sql, &[&id])?;
        self.from_row(row)
    }

    fn from_row(&self, row: Row) -> Result<Self::Entity, AppError>;
}
```

**Pattern 3 -- Macros for boilerplate (use sparingly):**

```rust
// When multiple structs need identical trait impls with minor variations,
// a declarative macro can reduce duplication without sacrificing readability.
macro_rules! impl_display_for_id {
    ($($t:ty),+) => {
        $(
            impl std::fmt::Display for $t {
                fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
                    write!(f, "{}", self.0)
                }
            }
        )+
    };
}

impl_display_for_id!(UserId, OrderId, ProductId);
```

### TypeScript

**Detection:**

```bash
npx jscpd --min-lines 10 src/
```

**Pattern -- Generics to eliminate type-specific duplication:**

```typescript
// BAD: separate fetch functions per entity
async function fetchUsers(): Promise<User[]> {
  const res = await fetch('/api/users');
  if (!res.ok) throw new ApiError(res.status);
  return res.json();
}

async function fetchOrders(): Promise<Order[]> {
  const res = await fetch('/api/orders');
  if (!res.ok) throw new ApiError(res.status);
  return res.json();
}

// GOOD: generic fetcher
async function fetchEntities<T>(endpoint: string): Promise<T[]> {
  const res = await fetch(`/api/${endpoint}`);
  if (!res.ok) throw new ApiError(res.status);
  return res.json();
}

const users = await fetchEntities<User>('users');
const orders = await fetchEntities<Order>('orders');
```

### Go

**Detection:**

```bash
jscpd --min-lines 10 --reporters console .

# PMD CPD also supports Go
pmd cpd --minimum-tokens 100 --language go --dir .
```

**Pattern -- Interface-based abstraction:**

```go
// BAD: duplicated marshal-and-write in each handler
func writeJSON(w http.ResponseWriter, data any) {
    w.Header().Set("Content-Type", "application/json")
    bytes, err := json.Marshal(data)
    if err != nil {
        http.Error(w, "marshal failed", 500)
        return
    }
    w.Write(bytes)
}
// This exact block appears in 8 handlers.

// GOOD: extract once, call everywhere (already shown above).
// If the pattern varies slightly per handler, use middleware.
```

### General

**When duplication is acceptable:**

- **Test setup code** that is specific to each test and would lose clarity if abstracted.
- **Two pieces of code that look similar today but serve different domains** and will likely
  diverge. Premature abstraction is worse than temporary duplication.
- **Generated code** that is produced by a code generator. Fix the generator, not the output.
- **Cross-service boundaries.** Sharing code between independently deployed services creates
  coupling. Duplication across service boundaries is often the lesser evil.

**Rule of three:** Do not extract on the first duplication. When the same pattern appears a
third time, extract. Two occurrences might be coincidence; three is a pattern.

## Prevention

- Run `jscpd` or `PMD CPD` in CI. Set a threshold (e.g., max 3% duplication) and fail the
  pipeline if exceeded.
- Code review checklist: "Is any block >10 lines copy-pasted from elsewhere in the codebase?"
- Maintain a shared utilities module per project. Document it so developers find existing
  helpers before writing new ones.
- When reviewing an MR that adds duplication, require the author to either extract or justify.
