# performance-tomographe

**Performance profiling and baseline scanner for the target project.** Measures latency, memory, VRAM usage, database performance, and context assembly timing. Produces baselines for regression detection and budget decomposition.

**Covers DR Sections:** S10 (Performance)

---

## Quick Start

```bash
# Full scan (all phases — requires running services)
"Read instruments/performance-tomographe/README.md and execute a full performance scan."

# Static analysis only (no running services needed)
"Read instruments/performance-tomographe/README.md and execute Phases 1-2 only (static analysis)."

# Baseline capture (requires running services)
"Read instruments/performance-tomographe/README.md and capture performance baselines."
```

---

## Scan Phases

| Phase | Name | What It Does | Requires Running Services? |
|-------|------|-------------|---------------------------|
| **1** | Architecture Profiling | Identify hot paths, async boundaries, allocation patterns from code | No |
| **2** | Database Analysis | Query patterns, index coverage, WAL configuration, table sizes | No (reads schema + code) |
| **3** | Latency Baseline | Measure p50/p95/p99 for key request paths | Yes |
| **4** | Memory & VRAM | Profile memory usage, VRAM allocation, leak detection | Yes |
| **5** | Throughput & Concurrency | Measure requests/second, concurrent connection handling | Yes |
| **6** | Context Assembly | Profile LLM context window assembly — RAG retrieval, history loading, prompt construction | Yes |
| **7** | Startup & Cold Path | Measure service startup time, first-request latency, cold cache behavior | Yes |
| **8** | Report | Compile findings with budget decomposition and regression detection | No |

---

## Phase 1 — Architecture Profiling (Static)

**Goal:** Identify performance-relevant patterns in the codebase without running anything.

### LLM steps

1. Read all source files handling inbound requests or running as long-lived loops (look for route handlers, server entrypoints, background workers, message consumers).
2. Identify blocking operations in async or concurrent contexts — the pattern varies by language but the concept is universal:
   - **Rust:** `std::thread::sleep`, `std::fs::read`/`write` in async functions (should be `tokio::time::sleep`, `tokio::fs` equivalents)
   - **Python:** `time.sleep()` inside `async def` functions (should be `asyncio.sleep()`), blocking file I/O in coroutines (should use `aiofiles` or run in executor)
   - **Go:** long-running synchronous calls inside goroutines without proper channel/context handling
   - **Node/TypeScript:** synchronous fs calls (`readFileSync`, `writeFileSync`, `execSync`) inside async handlers
3. Identify excessive object allocation or copying in hot paths: per-request allocation of large objects, deep cloning in request handlers, large serialisation operations on every request.
4. Identify lock contention points: mutexes, semaphores, or shared mutable state accessed frequently — note whether the lock type is appropriate for the runtime (e.g., async-aware vs OS-level locks).
5. Identify database connection handling: are connections opened per-request (bad) or pooled (good)?
6. Check that LLM/AI client calls have configurable timeouts.

### Accelerator tools (optional)

```bash
# Rust (if cargo/clippy available)
grep -rn 'std::thread::sleep\|std::fs::read\|std::fs::write' src/ --include='*.rs'

# Python (if available)
grep -rn 'time\.sleep\|open(' src/ --include='*.py' | grep -v 'asyncio\|aiofiles'

# Node/TypeScript (if available)
grep -rn 'readFileSync\|writeFileSync\|execSync' src/ --include='*.ts' --include='*.js'

# Go (if available)
grep -rn 'time\.Sleep\|ioutil\.ReadFile' . --include='*.go'
```

### Checklist

- [ ] No blocking I/O in async/concurrent request handlers
- [ ] Connections to databases and external services are pooled, not opened per request
- [ ] Per-request code avoids unnecessary large allocations or deep copies
- [ ] AI/LLM client has configurable timeout
- [ ] Lock types are appropriate for the runtime (e.g., async-aware locks in async code)
- [ ] No unnecessary deep cloning or copying in request hot path

---

## Phase 2 — Database Analysis (Static)

**Goal:** Analyze database schema and query patterns for performance concerns.

### LLM steps

1. Find all files containing SQL queries or ORM definitions — search for SQL keywords (`SELECT`, `INSERT`, `UPDATE`, `DELETE`, `CREATE TABLE`, `CREATE INDEX`) or ORM patterns (model definitions, migration files, schema files, entity annotations).
2. For each query: check whether frequently filtered columns have corresponding index definitions.
3. Look for `SELECT` statements without `WHERE` clauses in code that runs on large tables — potential full table scans.
4. Look for query calls inside loops — N+1 query pattern (a loop that executes one query per iteration rather than a single batched query).
5. Check that database connections are not opened inline in request handlers — connections should come from a pool or be reused across the request lifecycle.
6. Check for write-ahead logging or equivalent durability configuration for the database type in use (e.g., `journal_mode=WAL` for SQLite, `synchronous_commit` for PostgreSQL).

### Accelerator tools (optional)

```bash
# Find all SQL in any language
grep -rn 'SELECT\|INSERT\|UPDATE\|DELETE\|CREATE TABLE\|CREATE INDEX' \
  . --include='*.py' --include='*.ts' --include='*.go' --include='*.java' \
  --include='*.rb' --include='*.rs' 2>/dev/null | grep -v '/test'

# Index coverage across migration/schema files
grep -rn 'CREATE INDEX\|CREATE UNIQUE INDEX' . 2>/dev/null

# WAL/durability configuration
grep -rn 'journal_mode\|WAL\|wal_mode\|synchronous_commit' . 2>/dev/null

# Potential N+1: query calls near loop constructs
grep -rn 'SELECT\|\.find\|\.query\|\.execute' . 2>/dev/null | \
  grep -v '/test' | head -30
# Review manually for loop context
```

### Checklist

- [ ] WAL mode enabled on all databases (or equivalent durability setting)
- [ ] Busy timeout / connection timeout configured for concurrent access
- [ ] Indexes on all foreign key columns (`*_id`)
- [ ] Indexes on frequently filtered columns (created_at, status, domain)
- [ ] No full table scans in request hot path
- [ ] No N+1 query patterns
- [ ] Connection pooling or reuse (not open-per-query)

---

## Phase 3 — Latency Baseline (Live)

**Goal:** Measure request latency across key paths. Requires running services.

### LLM steps

Before measuring: review the latency budget table below and identify which endpoints map to which budget lines. Note any endpoints that do not have Prometheus metrics — those will require `curl` timing only.

After measuring: compare each p99/p95 result against the budget. Flag any path that exceeds its target. Identify the single largest contributor to end-to-end latency — that is the primary optimisation candidate.

### Accelerator tools (optional)

```bash
# Prerequisites: services running, test client configured
SERVICE_URL="http://localhost:8080"  # Adjust to actual URL

# Health endpoint (should be <10ms)
for i in $(seq 1 100); do
  curl -s -o /dev/null -w "%{time_total}\n" "$SERVICE_URL/health"
done | sort -n | awk '
  NR==50 {p50=$1} NR==95 {p95=$1} NR==99 {p99=$1}
  END {printf "Health: p50=%.3fs p95=%.3fs p99=%.3fs\n", p50, p95, p99}'

# API request (measures routing + DB + response)
# Requires auth token
TOKEN="Bearer $AUTH_TOKEN"
for i in $(seq 1 50); do
  curl -s -o /dev/null -w "%{time_total}\n" \
    -H "Authorization: $TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"content":"test message","thread_id":null}' \
    "$SERVICE_URL/api/v1/messages"
done | sort -n | awk '
  NR==25 {p50=$1} NR==47 {p95=$1} NR==49 {p99=$1}
  END {printf "API (no LLM): p50=%.3fs p95=%.3fs p99=%.3fs\n", p50, p95, p99}'

# Service request latency (direct call, StubLLM)
# Measure per-service latency if test endpoints exist

# Access control round-trip (action validation latency)
# Measured from service logs or Prometheus metrics:
# <service>_decision_duration_seconds
```

### Latency Budget

| Component | Target | Measurement Method |
|-----------|--------|--------------------|
| **Health check** | <10ms p99 | `curl` timing |
| **Auth validation** | <5ms p99 | Prometheus `<service>_auth_duration_seconds` |
| **Message routing** | <20ms p99 | Prometheus `<service>_router_duration_seconds` |
| **Access control round-trip** | <50ms p99 | Prometheus `<service>_decision_duration_seconds` |
| **DB query (single)** | <10ms p99 | Prometheus `<service>_db_query_duration_seconds` |
| **RAG retrieval** | <200ms p99 | Prometheus `<service>_rag_search_duration_seconds` |
| **Context assembly** | <500ms p99 | Phase 6 measurement |
| **LLM inference (first token)** | <2000ms p95 | Prometheus `<service>_llm_first_token_seconds` |
| **Full response** | <10s p95 | End-to-end measurement |

---

## Phase 4 — Memory & VRAM (Live)

**Goal:** Profile memory usage and detect leaks.

### LLM steps

Before measuring: review the threshold table below. Identify which Docker service names correspond to the primary, secondary, and auxiliary roles for this project — the service names in the `docker stats` output will need to be matched against those roles.

After measuring: check whether the memory timeseries shows a monotonically increasing trend (leak indicator) versus a plateau (acceptable). If VRAM usage is above 90% of the GPU total, flag for model quantisation review or offload configuration.

### Accelerator tools (optional)

```bash
# Container memory usage
docker stats --no-stream --format "{{.Name}}: {{.MemUsage}} ({{.MemPerc}})"

# Process RSS
ps aux | grep -E 'target_service' | \
  awk '{print $11, "RSS:", $6/1024, "MB"}'

# Memory over time (10-minute sample)
for i in $(seq 1 60); do
  docker stats --no-stream --format "{{.Name}},{{.MemUsage}}"
  sleep 10
done > output/YYYY-MM-DD_{project_name}/scratch/performance/memory-timeseries.csv

# VRAM usage (GPU)
nvidia-smi --query-gpu=memory.used,memory.total,memory.free \
  --format=csv,noheader,nounits 2>/dev/null

# VRAM per process
nvidia-smi --query-compute-apps=pid,used_memory,name \
  --format=csv,noheader 2>/dev/null

# Check for memory growth pattern (leak indicator)
# Compare first and last readings from timeseries
# Growth >10% over 10 minutes under idle = potential leak
```

### Thresholds

| Component | Target | Severity if Exceeded |
|-----------|--------|---------------------|
| Primary service RSS | <500MB idle, <1GB active | Major if >1.5GB |
| Secondary service RSS | <50MB | Major if >100MB |
| Auxiliary service RSS | <30MB | Major if >80MB |
| VRAM (idle, model loaded) | Per model tier (see config) | Observation if >90% |
| Memory growth (1h idle) | <5% | Major if >10% (leak) |

---

## Phase 5 — Throughput & Concurrency (Live)

**Goal:** Measure system behavior under concurrent load.

### LLM steps

Before measuring: check from Phase 1 findings whether any shared mutable state or lock contention was identified. Those are the most likely failure points under concurrent load — pay particular attention to them in the results.

After measuring: if any concurrent requests return non-200 status codes or show significantly elevated latency, cross-reference with Phase 1 lock contention findings and Phase 2 connection pooling findings. Serialised access through a single lock is the most common root cause.

### Accelerator tools (optional)

```bash
# Concurrent connections (WebSocket)
# Open N simultaneous WebSocket connections, measure stability
# Use a simple script or tool like wscat/websocat

# Concurrent API messages
# Send 10 messages concurrently, measure all complete successfully
for i in $(seq 1 10); do
  curl -s -o /dev/null -w "%{http_code} %{time_total}\n" \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d "{\"content\":\"concurrent test $i\"}" \
    "$SERVICE_URL/api/v1/messages" &
done
wait

# SQLite concurrent writes (stress test)
# Reference: existing test_concurrent_writes test (10 processes x 1000 writes)
# Just verify it still passes and check timing

# Database contention under load
# Monitor PRAGMA busy_timeout hits during concurrent operations
```

### Thresholds

| Scenario | Target | Severity if Missed |
|----------|--------|--------------------|
| 5 concurrent API messages | All 200 OK, p95 <500ms | Minor |
| 10 concurrent DB writes | Zero errors, zero corruption | Major |
| 5 concurrent WebSocket sessions | All stable for 60s | Minor |
| SQLite WAL checkpoint during load | No blocking, <100ms | Observation |

---

## Phase 6 — Context Assembly (Live)

**Goal:** Profile the LLM context window assembly pipeline — the critical path between user message and LLM invocation.

### LLM steps

Before measuring: locate the context assembly code path in the codebase (search for terms like `build_context`, `assemble_prompt`, `context_assembly`, or equivalent). Determine whether timing instrumentation already exists (Prometheus metrics or structured log entries). If it does not, the grep in the accelerator block will confirm.

After measuring: compare each stage's contribution against the budget decomposition table. If total assembly time exceeds 500ms p95, identify the single largest stage — that is where optimisation effort should focus first. RAG retrieval and history loading are the most common bottlenecks.

### Accelerator tools (optional)

```bash
# Context assembly components:
# 1. System prompt loading (config)
# 2. RAG retrieval (vector search)
# 3. Conversation history loading (database)
# 4. Service context injection
# 5. Token counting and truncation
# 6. Final prompt construction

# Measure each component separately via Prometheus metrics or instrumented logging
# Key metrics:
# <service>_context_system_prompt_ms
# <service>_context_rag_retrieval_ms
# <service>_context_history_load_ms
# <service>_context_service_context_ms
# <service>_context_token_count_ms
# <service>_context_total_ms

# If metrics don't exist yet, check whether timing instrumentation exists:
grep -rn 'context_assembl\|build_context\|assemble_prompt' . \
  --include='*.py' --include='*.ts' --include='*.go' --include='*.rs' 2>/dev/null

# Token budget analysis
# How close to limit is the typical assembled context?
# Check actual token counts in logs/metrics
```

### Budget Decomposition

| Stage | Budget | Priority |
|-------|--------|----------|
| System prompt | 15-20% of context window | Fixed |
| RAG retrieval | 30-40% | Critical — directly impacts answer quality |
| Conversation history | 30-40% | Important for continuity |
| Generation headroom | 10% minimum | Non-negotiable |
| **Total assembly time** | **<500ms p95** | Target |

---

## Phase 7 — Startup & Cold Path (Live)

**Goal:** Measure cold-start behavior.

### LLM steps

Before measuring: check whether the service has a documented startup sequence (e.g., model loading, vector index warming, database migration). Understanding the expected sequence helps distinguish a slow-but-correct startup from an actual fault.

After measuring: if any service exceeds its ready threshold, check logs from that service's startup window. The most common causes are synchronous model loading, sequential dependency waiting, or a cold vector index that must be rebuilt on first query.

### Accelerator tools (optional)

```bash
# Full stack startup time
time docker compose up -d 2>&1
# Measure from command to all health checks passing

# Per-service startup
for svc in $(docker compose config --services); do
  docker compose up -d $svc
  start=$(date +%s%N)
  until docker compose exec $svc curl -sf localhost:*/health 2>/dev/null; do
    sleep 0.1
  done
  end=$(date +%s%N)
  echo "$svc: $(( (end - start) / 1000000 ))ms"
done

# First-request latency (cold cache)
# After fresh start, time the first API request
# This includes model loading, first vector search, first DB query

# Model loading time
# Time from service start to first successful LLM inference
# Check logs for model loading indicators
```

### Thresholds

| Metric | Target | Severity |
|--------|--------|----------|
| Full stack cold start | <60s | Minor if >60s, Major if >120s |
| Primary service ready (health OK) | <15s | Minor if >30s |
| Secondary service ready | <5s | Minor if >10s |
| First API response (cold) | <30s (includes model load) | Observation |
| First API response (warm) | <5s | Minor if >10s |

---

## Phase 8 — Report

Compile all phase outputs into `output/YYYY-MM-DD_{project_name}/PS{n}-performance-tomographe.md` (see `qualitoscope/config.yaml` for `project_name`).

Include:
- Latency budget decomposition table
- Memory usage summary
- Regression detection (vs previous run)
- Hot path identification
- Recommendations prioritized by impact

---

## Directory Structure

```
performance-tomographe/
├── README.md
├── config.yaml
├── methods/
│   ├── 01-architecture-profiling.md
│   ├── 02-database-analysis.md
│   ├── 03-latency-baseline.md
│   ├── 04-memory-vram.md
│   ├── 05-throughput-concurrency.md
│   ├── 06-context-assembly.md
│   ├── 07-startup-cold-path.md
│   └── 08-report.md
├── checklists/
│   ├── async-patterns.md              # Blocking-in-async detection
│   ├── database-performance.md        # Index coverage, query patterns
│   └── vram-budget.md                 # Per-model VRAM allocation
├── templates/
│   └── report-template.md
# output is centralised — see output/YYYY-MM-DD_{project_name}/
└── fixes/
    └── README.md
```

---

## Configuration

This instrument reads project-specific paths from `project-profile.yaml` in the target project root. If a profile field is absent, the default from the profile schema applies. Instrument-specific thresholds remain in this instrument's `config.yaml`.

```yaml
thresholds:
  latency:
    health_p99_ms: 10
    auth_p99_ms: 5
    router_p99_ms: 20
    access_control_p99_ms: 50
    db_query_p99_ms: 10
    rag_search_p99_ms: 200
    context_assembly_p95_ms: 500
    llm_first_token_p95_ms: 2000
    full_response_p95_ms: 10000

  memory:
    primary_service_idle_max_mb: 500
    primary_service_active_max_mb: 1000
    secondary_service_max_mb: 50
    auxiliary_service_max_mb: 30
    growth_1h_max_percent: 5

  vram:
    gpu_total_gb: 16
    model_8b_q4_gb: 5
    model_32b_q4_gb: 18
    warn_utilization_percent: 90

  throughput:
    concurrent_messages_min: 5
    concurrent_ws_sessions_min: 5

  startup:
    full_stack_max_seconds: 60
    primary_service_ready_max_seconds: 15
    secondary_service_ready_max_seconds: 5

scope:
  service_url: "http://localhost:8080"
  requires_auth: true
  measure_duration_minutes: 10
```

---

## Run History

| Run | Date | Trigger | Key Finding | Report |
|-----|------|---------|-------------|--------|
| PS1 | _pending_ | Initial baseline | — | — |

## License

Part of [qual-gate](https://github.com/Nelvradia/qual-gate). Licensed under [Apache 2.0](../../LICENSE).
