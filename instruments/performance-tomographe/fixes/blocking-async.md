---
title: "Fix: Blocking Calls in Async Context"
status: current
last-updated: 2026-03-19
instrument: performance-tomographe
severity-range: "Major–Critical"
---

# Fix: Blocking Calls in Async Context

## What this means

A blocking operation — synchronous I/O, CPU-intensive computation, or a sleep call — is running
on an async runtime's executor thread. Async runtimes (asyncio, tokio, Node.js event loop, Go
scheduler) multiplex many tasks onto a small number of threads. When one task blocks a thread,
all other tasks scheduled on that thread stall. This causes tail latency spikes, request timeouts,
and in severe cases complete service unresponsiveness even under moderate load. A single blocking
call in a hot path can reduce your service's effective concurrency from thousands of concurrent
requests to the number of OS threads in the runtime's pool.

## How to fix

### Python

**Identify blocking calls in async code:**

Common offenders: `time.sleep()`, `requests.get()`, `open().read()`, `subprocess.run()`,
`socket` operations, database drivers without async support.

**Offload blocking I/O to a thread pool:**

```python
import asyncio
import functools
from concurrent.futures import ThreadPoolExecutor

# Create a dedicated thread pool (size it to your workload)
BLOCKING_POOL = ThreadPoolExecutor(max_workers=10, thread_name_prefix="blocking")


async def fetch_legacy_api(url: str) -> str:
    """Wrap a blocking HTTP call for use in async context."""
    import requests  # synchronous library

    loop = asyncio.get_running_loop()
    response = await loop.run_in_executor(
        BLOCKING_POOL,
        functools.partial(requests.get, url, timeout=10),
    )
    return response.text


# Better: use an async HTTP client instead of wrapping
import httpx

async def fetch_api_async(url: str) -> str:
    """Use a native async HTTP client — no thread pool needed."""
    async with httpx.AsyncClient() as client:
        response = await client.get(url, timeout=10)
        return response.text
```

**Offload CPU-intensive work to a process pool:**

```python
import asyncio
from concurrent.futures import ProcessPoolExecutor

COMPUTE_POOL = ProcessPoolExecutor(max_workers=4)


def heavy_computation(data: bytes) -> bytes:
    """CPU-bound work that would block the event loop."""
    import hashlib
    # Simulate expensive computation
    for _ in range(100_000):
        data = hashlib.sha256(data).digest()
    return data


async def process_data(data: bytes) -> bytes:
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(COMPUTE_POOL, heavy_computation, data)
```

**Replace blocking calls with async equivalents:**

| Blocking | Async replacement |
|----------|-------------------|
| `requests` | `httpx`, `aiohttp` |
| `time.sleep()` | `asyncio.sleep()` |
| `open().read()` | `aiofiles.open()` |
| `subprocess.run()` | `asyncio.create_subprocess_exec()` |
| `psycopg2` | `psycopg` (v3 async), `asyncpg` |
| `redis.Redis()` | `redis.asyncio.Redis()` |

### Rust

**Identify blocking calls in async Tokio context:**

Common offenders: `std::thread::sleep()`, `std::fs::read()`, synchronous database drivers,
`reqwest::blocking`, CPU-heavy loops without yielding.

**Use `tokio::task::spawn_blocking` for unavoidable blocking:**

```rust
use tokio::task;

async fn read_large_file(path: &str) -> Result<Vec<u8>, std::io::Error> {
    let path = path.to_owned();
    // Moves the blocking call to tokio's dedicated blocking thread pool
    task::spawn_blocking(move || std::fs::read(&path)).await?
}

// For CPU-intensive work
async fn compute_hash(data: Vec<u8>) -> Vec<u8> {
    task::spawn_blocking(move || {
        use sha2::{Sha256, Digest};
        let mut hasher = Sha256::new();
        hasher.update(&data);
        hasher.finalize().to_vec()
    })
    .await
    .expect("blocking task panicked")
}
```

**Prefer async-native APIs:**

```rust
// Instead of std::fs — use tokio::fs
use tokio::fs;

async fn read_config(path: &str) -> Result<String, std::io::Error> {
    fs::read_to_string(path).await
}

// Instead of std::thread::sleep — use tokio::time::sleep
use tokio::time::{sleep, Duration};

async fn retry_with_backoff() {
    sleep(Duration::from_secs(1)).await; // Non-blocking
}
```

### TypeScript

**Identify blocking calls in the Node.js event loop:**

Common offenders: `fs.readFileSync()`, `crypto.pbkdf2Sync()`, CPU-heavy loops,
`JSON.parse()` on very large payloads, synchronous `child_process.execSync()`.

**Use async APIs and worker threads:**

```typescript
import { readFile } from "fs/promises"; // Async, not fs.readFileSync
import { Worker, isMainThread, parentPort, workerData } from "worker_threads";
import { promisify } from "util";
import { pbkdf2 } from "crypto";

const pbkdf2Async = promisify(pbkdf2);

// Async file I/O (non-blocking)
async function loadConfig(path: string): Promise<string> {
  return readFile(path, "utf-8");
}

// Async crypto (non-blocking — uses libuv thread pool)
async function hashPassword(password: string, salt: Buffer): Promise<Buffer> {
  return pbkdf2Async(password, salt, 100_000, 64, "sha512");
}

// Worker thread for CPU-intensive tasks
function runInWorker<T>(workerPath: string, data: unknown): Promise<T> {
  return new Promise((resolve, reject) => {
    const worker = new Worker(workerPath, { workerData: data });
    worker.on("message", resolve);
    worker.on("error", reject);
    worker.on("exit", (code) => {
      if (code !== 0) {
        reject(new Error(`Worker exited with code ${code}`));
      }
    });
  });
}
```

### Go

Go's goroutine scheduler is preemptive (since Go 1.14), so blocking a goroutine does not block
the entire runtime. However, blocking all OS threads in the runtime thread pool (default =
`GOMAXPROCS`) will stall the scheduler. Excessive goroutine blocking also wastes memory and
degrades throughput.

**Avoid blocking the runtime thread pool:**

```go
import (
    "context"
    "runtime"
    "time"
)

// CGo calls block the OS thread. Use a bounded worker pool.
func callBlockingCgo(ctx context.Context, work func()) error {
    sem := make(chan struct{}, runtime.GOMAXPROCS(0))
    select {
    case sem <- struct{}{}:
        defer func() { <-sem }()
        work()
        return nil
    case <-ctx.Done():
        return ctx.Err()
    }
}

// For CPU-intensive work, limit concurrent goroutines
func processItems(items []Item, concurrency int) []Result {
    sem := make(chan struct{}, concurrency)
    results := make([]Result, len(items))

    var wg sync.WaitGroup
    for i, item := range items {
        wg.Add(1)
        sem <- struct{}{}
        go func(i int, item Item) {
            defer wg.Done()
            defer func() { <-sem }()
            results[i] = heavyComputation(item)
        }(i, item)
    }
    wg.Wait()
    return results
}
```

### General

**How to detect blocking calls:**

- **Load test with concurrency:** Send 100+ concurrent requests. If throughput plateaus at a
  number matching your thread pool size, you have a blocking call.
- **Monitor event loop / runtime metrics:** asyncio loop lag, tokio task poll duration, Node.js
  event loop utilisation, Go scheduler latency.
- **Profiling:** CPU flame graphs will show long synchronous stacks on runtime threads.
- **Static analysis:** Some linters can detect sync calls in async contexts (e.g., `ruff` rule
  `ASYNC100` for Python, `clippy::await_holding_lock` for Rust).

**Decision tree: offload vs. replace:**

1. Is there an async-native library? -> Use it. (Best option.)
2. Is the blocking call I/O-bound? -> Offload to a thread pool.
3. Is the blocking call CPU-bound? -> Offload to a process pool (Python) or `spawn_blocking`
   with a sized pool (Rust). In Node.js, use worker threads.
4. Is it a brief blocking call (< 1ms)? -> Acceptable in most cases. Document why.

## Prevention

**Linting for blocking calls in async code:**

```yaml
# ruff.toml (Python)
[lint]
select = ["ASYNC"]  # Detects blocking calls in async functions

# .clippy.toml (Rust) — clippy catches some patterns by default:
# - await_holding_lock
# - await_holding_refcell_ref
```

**CI performance gate:**

```yaml
# GitLab CI — detect event loop blocking under load
async-blocking-test:
  stage: test
  script:
    - |
      # Start the service
      python -m myapp &
      sleep 2
      # Send concurrent requests, measure tail latency
      wrk -t4 -c100 -d10s http://localhost:8080/health | tee wrk.out
      # Fail if p99 latency exceeds threshold
      P99=$(grep "99%" wrk.out | awk '{print $2}')
      echo "p99 latency: $P99"
      # Parse and compare against budget (implementation depends on output format)
  allow_failure: false
```

**Runtime monitoring:**

- Instrument your async runtime's internal metrics. Tokio exposes task poll times via
  `tokio-metrics`. Python's asyncio has `loop.slow_callback_duration`. Node.js has
  `perf_hooks.monitorEventLoopDelay()`.
- Alert when event loop lag exceeds 100ms sustained. This catches blocking regressions before
  they reach production.
