---
title: "Fix: Excessive Allocation"
status: current
last-updated: 2026-03-19
instrument: performance-tomographe
severity-range: "Minor–Major"
---

# Fix: Excessive Allocation

## What this means

Your code allocates significantly more memory than necessary for its workload — creating
temporary objects in tight loops, copying data instead of borrowing, building intermediate
collections that are immediately discarded, or failing to reuse buffers across operations.
Excessive allocation increases GC pressure (Python, Go, TypeScript), causes latency spikes during
garbage collection pauses, wastes CPU on allocation/deallocation, and can lead to OOM kills in
memory-constrained environments like containers. Even in Rust (no GC), excessive heap allocation
degrades cache locality and throughput. Profiling typically reveals that 80% of allocations come
from a few hot paths — fixing those paths yields disproportionate improvement.

## How to fix

### Python

**Reuse objects and avoid unnecessary copies:**

```python
from __future__ import annotations

# BAD: creates a new list on every call
def process_items_bad(items: list[dict]) -> list[str]:
    return [item["name"].upper() for item in items]  # Intermediate list

# GOOD: use a generator when downstream consumes one-at-a-time
def process_items(items: list[dict]) -> Iterator[str]:
    return (item["name"].upper() for item in items)  # Generator, no list


# BAD: string concatenation in a loop (creates N intermediate strings)
def build_csv_bad(rows: list[list[str]]) -> str:
    result = ""
    for row in rows:
        result += ",".join(row) + "\n"  # O(N^2) due to string copying
    return result

# GOOD: use join or io.StringIO
import io

def build_csv(rows: list[list[str]]) -> str:
    buf = io.StringIO()
    for row in rows:
        buf.write(",".join(row))
        buf.write("\n")
    return buf.getvalue()
```

**Use `__slots__` for data-heavy classes (saves ~200 bytes per instance):**

```python
class Point:
    __slots__ = ("x", "y", "z")

    def __init__(self, x: float, y: float, z: float) -> None:
        self.x = x
        self.y = y
        self.z = z
```

**Profile with `tracemalloc` (stdlib) or `memory-profiler`:**

```bash
# memory-profiler: line-by-line memory profiling
pip install memory-profiler && python -m memory_profiler my_script.py
```

```python
# tracemalloc: allocation tracking (stdlib, no install needed)
import tracemalloc
tracemalloc.start()
# ... run your code ...
for stat in tracemalloc.take_snapshot().statistics("lineno")[:10]:
    print(stat)
```

### Rust

**Avoid unnecessary cloning — borrow instead:**

```rust
// BAD: cloning a large string just to read it
fn process_bad(data: &str) -> String {
    let owned = data.to_string(); // Unnecessary heap allocation
    owned.to_uppercase()
}

// GOOD: borrow the input, allocate only for the output
fn process(data: &str) -> String {
    data.to_uppercase() // Only one allocation for the result
}

// BAD: collecting into Vec just to iterate
fn sum_bad(items: &[Item]) -> f64 {
    let values: Vec<f64> = items.iter().map(|i| i.value).collect(); // Wasteful
    values.iter().sum()
}

// GOOD: chain iterators without intermediate collection
fn sum(items: &[Item]) -> f64 {
    items.iter().map(|i| i.value).sum()
}
```

**Reuse buffers across operations:**

```rust
use std::io::Read;

// BAD: allocates a new Vec on every call
fn read_all_bad(reader: &mut impl Read) -> Vec<u8> {
    let mut buf = Vec::new();
    reader.read_to_end(&mut buf).unwrap();
    buf
}

// GOOD: caller provides a reusable buffer
fn read_all(reader: &mut impl Read, buf: &mut Vec<u8>) -> usize {
    buf.clear();              // Reuse the allocation, just reset length
    reader.read_to_end(buf).unwrap()
}

// Usage in a loop:
let mut buf = Vec::with_capacity(4096); // Allocate once
for reader in readers {
    let n = read_all(&mut reader, &mut buf);
    process(&buf[..n]);
}
```

**Profile with DHAT or heaptrack:**

```bash
# DHAT (Valgrind tool — detailed allocation profiling)
cargo build --release
valgrind --tool=dhat ./target/release/myapp
# Open dhat-out.html in a browser for interactive analysis

# heaptrack (lower overhead, good for long-running services)
heaptrack ./target/release/myapp
heaptrack_gui heaptrack.myapp.*.zst

# cargo-instruments (macOS)
cargo instruments -t Allocations --release
```

### TypeScript

**Avoid object spread and array copies in hot paths:**

```typescript
// BAD: creates a new object on every iteration
function enrichItems(items: Item[]): EnrichedItem[] {
  return items.map((item) => ({
    ...item,          // Shallow copy of every property
    enriched: true,
    timestamp: Date.now(),
  }));
}

// GOOD: mutate in place if the original is not needed
function enrichItemsInPlace(items: Item[]): void {
  for (const item of items) {
    (item as EnrichedItem).enriched = true;
    (item as EnrichedItem).timestamp = Date.now();
  }
}

// BAD: Array.concat in a loop (O(N^2) allocations)
function flattenBad(arrays: number[][]): number[] {
  let result: number[] = [];
  for (const arr of arrays) {
    result = result.concat(arr); // New array every iteration
  }
  return result;
}

// GOOD: flat() or push with spread
function flatten(arrays: number[][]): number[] {
  return arrays.flat();
}
```

### Go

**Reuse objects with `sync.Pool`:**

```go
import (
    "bytes"
    "sync"
)

// Pool of reusable byte buffers
var bufPool = sync.Pool{
    New: func() interface{} {
        return new(bytes.Buffer)
    },
}

func processRequest(data []byte) string {
    buf := bufPool.Get().(*bytes.Buffer)
    defer func() {
        buf.Reset()
        bufPool.Put(buf)
    }()

    buf.Write(data)
    // ... process buffer ...
    return buf.String()
}
```

**Pre-allocate slices and maps when size is known:**

```go
// BAD: append grows the slice multiple times (realloc + copy each time)
func collectIDs(items []Item) []string {
    var ids []string
    for _, item := range items {
        ids = append(ids, item.ID)
    }
    return ids
}

// GOOD: pre-allocate with known capacity
func collectIDs(items []Item) []string {
    ids := make([]string, 0, len(items)) // One allocation
    for _, item := range items {
        ids = append(ids, item.ID)
    }
    return ids
}

// Same for maps
m := make(map[string]int, expectedSize)
```

### General

**Allocation reduction strategies (ranked by impact):**

1. **Eliminate unnecessary work.** The fastest allocation is one that never happens. Question
   whether intermediate data structures are needed at all.
2. **Reuse buffers and objects.** Object pools, buffer pools, or clearing and reusing
   collections instead of creating new ones.
3. **Pre-allocate when size is known.** Avoid repeated grow-and-copy cycles in arrays, vectors,
   and string builders.
4. **Use iterators/generators over materialised collections.** Process data element-by-element
   instead of collecting into memory.
5. **Choose compact data representations.** `__slots__`, struct-of-arrays vs. array-of-structs,
   columnar formats for tabular data.

## Prevention

**CI memory budget checks:**

```yaml
# GitLab CI — fail if memory exceeds budget under load test
memory-budget:
  stage: test
  script:
    - |
      # Run the service with a memory limit
      docker run --memory=256m --name sut myapp &
      sleep 5
      # Load test
      wrk -t2 -c20 -d30s http://localhost:8080/api/items
      # Check if container was OOM-killed
      STATUS=$(docker inspect sut --format='{{.State.OOMKilled}}')
      if [ "$STATUS" = "true" ]; then
        echo "ERROR: Service exceeded 256 MB memory budget"
        exit 1
      fi
  allow_failure: false
```

**Benchmark-driven regression detection:**

- Rust: use `criterion` benchmarks with `cargo bench`. Compare against baseline.
- Go: use `testing.B` benchmarks. `go test -bench=. -benchmem` reports allocations per op.
- Python: use `pytest-benchmark` with `--benchmark-compare` to detect regressions.

**Review checklist:**

- Any new allocation in a loop body or request handler should be justified.
- String concatenation in loops should use builders or join patterns.
- Collection sizes should be pre-allocated when known.
- Large temporary objects should be reused via pools or cleared-and-reused patterns.
