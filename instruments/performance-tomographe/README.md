# .performance-tomographe/

**Performance profiling and baseline scanner for the target project.** Measures latency, memory, VRAM usage, database performance, and context assembly timing. Produces baselines for regression detection and budget decomposition.

**Covers DR Sections:** S10 (Performance)

---

## Quick Start

```bash
# Full scan (all phases — requires running services)
"Read .performance-tomographe/README.md and execute a full performance scan."

# Static analysis only (no running services needed)
"Read .performance-tomographe/README.md and execute Phases 1-2 only (static analysis)."

# Baseline capture (requires running services)
"Read .performance-tomographe/README.md and capture performance baselines."
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

### Steps

```bash
# Async boundaries — find blocking calls in async context
grep -rn 'std::thread::sleep\|std::fs::\|std::io::Read' src/ --include='*.rs'
# These should be tokio equivalents in async code

# Large allocations
grep -rn 'Vec::new\|String::new\|vec!\[' src/ --include='*.rs' | \
  grep -v 'test\|#\[test\]' | head -30
# Look for allocations in hot paths (request handlers, service execution)

# Clone patterns in hot paths
grep -rn '\.clone()' src/api/ src/services/ --include='*.rs' | wc -l

# Mutex contention points
grep -rn 'Mutex\|RwLock\|Arc<Mutex' src/ --include='*.rs'
# Tokio mutex vs std mutex in async context

# Database connection pooling
grep -rn 'pool\|Pool\|connection\|Connection' src/db/ --include='*.rs'

# Serialization in hot paths
grep -rn 'serde_json::to_string\|serde_json::from_str\|to_vec\|from_slice' \
  src/api/ src/services/ --include='*.rs' | wc -l

# LLM client timeout configuration
grep -rn 'timeout\|Timeout\|Duration' src/llm/ --include='*.rs'
```

### Checklist

- [ ] No `std::thread::sleep` in async context (use `tokio::time::sleep`)
- [ ] No blocking filesystem I/O in async handlers (use `tokio::fs`)
- [ ] Tokio `Mutex` used instead of `std::sync::Mutex` in async code
- [ ] Database connections pooled (not opened per-request)
- [ ] LLM client has configurable timeout
- [ ] No unnecessary `.clone()` in request hot path
- [ ] Large allocations avoided in per-request code

---

## Phase 2 — Database Analysis (Static)

**Goal:** Analyze database schema and query patterns for performance concerns.

### Steps

```bash
# Table row count estimation (from migration files or schema)
# List all CREATE TABLE statements
grep -rn 'CREATE TABLE' src/db/ --include='*.rs' | wc -l

# Index coverage
grep -rn 'CREATE INDEX\|CREATE UNIQUE INDEX' src/db/ --include='*.rs'

# Check for missing indexes on foreign key columns
# Find all columns ending in _id that aren't indexed
grep -rn '_id\s' src/db/ --include='*.rs' | grep -v 'CREATE INDEX' | grep 'INTEGER\|TEXT'

# WAL mode configuration
grep -rn 'journal_mode\|WAL\|wal_mode' src/db/ config/ --include='*.rs' --include='*.yaml'

# Full table scans (SELECT without WHERE or with LIKE '%...%')
grep -rn 'SELECT.*FROM' src/db/ --include='*.rs' | grep -v 'WHERE' | head -10

# N+1 query patterns (loops containing queries)
# Look for query calls inside for/while loops
grep -B5 'execute\|query_row\|query_map' src/db/ --include='*.rs' | grep -E 'for |while '

# Connection handling
grep -rn 'open_with_flags\|Connection::open' src/db/ --include='*.rs'
# Should use connection pooling, not open-per-query

# Busy timeout for concurrent access
grep -rn 'busy_timeout\|busy_handler' src/db/ --include='*.rs'
```

### Checklist

- [ ] WAL mode enabled on all databases
- [ ] Busy timeout configured (>=5000ms for concurrent access)
- [ ] Indexes on all foreign key columns (`*_id`)
- [ ] Indexes on frequently filtered columns (created_at, status, domain)
- [ ] No full table scans in request hot path
- [ ] No N+1 query patterns
- [ ] Connection pooling or reuse (not open-per-query)
- [ ] PRAGMA `synchronous = NORMAL` for WAL mode (not FULL)

---

## Phase 3 — Latency Baseline (Live)

**Goal:** Measure request latency across key paths. Requires running services.

### Steps

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

### Steps

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
done > output/memory-timeseries.csv

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

### Steps

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

### Steps

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

# If metrics don't exist yet, use structured logging:
grep -rn 'context_assembl\|build_context\|assemble_prompt' src/ --include='*.rs'
# Check if timing instrumentation exists

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

### Steps

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

Compile all phase outputs into `output/YYYY-MM-DD/PS{n}-performance-tomographe.md`.

Include:
- Latency budget decomposition table
- Memory usage summary
- Regression detection (vs previous run)
- Hot path identification
- Recommendations prioritized by impact

---

## Directory Structure

```
.performance-tomographe/
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
├── output/
│   └── .gitignore
└── fixes/
    └── README.md
```

---

## Configuration

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
