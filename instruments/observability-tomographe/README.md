# observability-tomographe/

**Observability health scanner.** Audits metrics coverage, alerting rules, log quality, dashboards, health endpoints, and audit trail completeness.

**Covers Sections:** S7 (Observability & Monitoring)

---

## Quick Start

```bash
"Read instruments/observability-tomographe/README.md and execute a full observability scan."
"Read instruments/observability-tomographe/README.md and execute Phase 2 (Alerting Rules) only."
```

---

## Scan Phases

| Phase | Name | What It Does | Requires Running Services? |
|-------|------|-------------|---------------------------|
| **1** | Metrics Coverage | Compare metrics registry docs vs actual registered metrics | No |
| **2** | Alerting Rules | Validate alert rules, thresholds, routing | No |
| **3** | Log Quality | Audit structured logging format, levels, sensitive data | No |
| **4** | Dashboard Health | Validate dashboards reference real metrics | No (reads JSON) |
| **5** | Health Endpoints | Verify health check implementation and response format | Partial |
| **6** | Audit Trail | Verify access control decisions, security events are logged | No |
| **7** | Report | Compile findings | No |

---

## Phase 1 — Metrics Coverage

**Goal:** Verify that all documented metrics are actually registered in code, and all registered metrics are documented.

### LLM steps

1. Read source files in the directories listed under `scope.metrics_source_dirs` to identify where metrics are emitted. The implementation varies by language and library (Prometheus client in Rust/Python/Go/Java, StatsD, OpenTelemetry, etc.) but all share a pattern: metric registration with a name and type, followed by increment/observe/set calls.
2. Compare discovered metrics against the metrics documentation file specified in `scope.metrics_doc`.
3. Check that key system events are instrumented: request counts, request latency, error rates, queue depths, database query counts/latency — these are universal regardless of language.
4. Look for metrics documentation (a metrics registry file, a Prometheus scrape config, or equivalent) and verify it matches what is in the code.

### Accelerator tools (optional)

```bash
# Rust — prometheus / prometheus-client crates
grep -rn 'register_counter\|register_histogram\|register_gauge\|counter!\|histogram!\|gauge!\|IntCounter\|Histogram\|Gauge' \
  src/ --include='*.rs' 2>/dev/null | grep -oP '[a-z][a-z0-9_]+' | sort -u

# Python — prometheus_client library
grep -rn 'Counter(\|Histogram(\|Gauge(\|Summary(\|register(' \
  src/ --include='*.py' 2>/dev/null | grep -oP '[a-z][a-z0-9_]+' | sort -u

# Go — prometheus/client_golang
grep -rn 'prometheus\.NewCounter\|prometheus\.NewHistogram\|prometheus\.NewGauge\|MustRegister' \
  . --include='*.go' 2>/dev/null | grep -oP '[a-z][a-z0-9_]+' | sort -u

# Java — Micrometer / prometheus_simpleclient
grep -rn 'Counter\.builder\|Histogram\.build\|Gauge\.builder\|registry\.register' \
  src/ --include='*.java' 2>/dev/null | grep -oP '[a-z][a-z0-9_]+' | sort -u

# OpenTelemetry (language-agnostic pattern)
grep -rn 'createCounter\|createHistogram\|createGauge\|createObservableGauge' \
  src/ 2>/dev/null | grep -oP '[a-z][a-z0-9_]+' | sort -u

# Metrics referenced in documentation
grep -oP '[a-z][a-z0-9_]+' docs/metrics-registry.md 2>/dev/null | sort -u > /tmp/doc_metrics.txt
```

### Severity Rules

| Finding | Severity |
|---------|----------|
| Core metric documented but not registered (e.g., decision latency) | **Minor** |
| Metric registered but not documented (unknown purpose) | **Observation** |
| Metric not following naming convention | **Observation** |
| Zero metrics registered (no observability) | **Critical** |
| <50% of documented metrics registered | **Major** |

---

## Phase 2 — Alerting Rules

**Goal:** Validate alerting rules are correct and useful.

### LLM steps

1. Read alert rule files (Prometheus rules, PagerDuty config, Grafana alerts, or equivalent) from the paths listed in `scope.alert_rules`.
2. Verify that critical system states have alerts: service down, error rate spike, resource exhaustion.
3. Check alert thresholds against the metrics documentation to confirm the referenced metric names exist and the threshold values are realistic.

### Accelerator tools (optional)

```bash
# Locate alert rule files
find config/ infra/ -name '*.rules.yml' -o -name 'alerts.yml' -o -name '*.rules' 2>/dev/null

# Validate with promtool (if available)
for f in $(find config/ infra/ -name '*.rules.yml' -o -name '*.rules' 2>/dev/null); do
  promtool check rules "$f" 2>&1 || echo "PROMTOOL_UNAVAILABLE: manual review needed for $f"
done

# Count alert rules
grep -c 'alert:' config/prometheus/*.rules.yml infra/prometheus/*.rules.yml 2>/dev/null

# Check for critical alert names (adapt to your service names)
for alert in "ServiceDown" "HighMemoryUsage" "DiskSpaceLow" "HighErrorRate" "CertificateExpiry" "BackupFailed"; do
  grep -q "$alert" config/prometheus/*.rules.yml infra/prometheus/*.rules.yml 2>/dev/null && \
    echo "OK: $alert exists" || echo "MISSING: $alert"
done

# Alertmanager routing
find config/ infra/ -name 'alertmanager.yml' 2>/dev/null
grep -A5 'receivers:' config/alertmanager.yml infra/alertmanager.yml 2>/dev/null | head -20

# Alert severity labels
grep 'severity:' config/prometheus/*.rules.yml infra/prometheus/*.rules.yml 2>/dev/null | sort | uniq -c
```

### Required Alert Rules

- [ ] Service process down (for each service)
- [ ] High memory usage (>80% container limit)
- [ ] Disk space low (<10% free)
- [ ] High error rate (>5% of requests returning 5xx)
- [ ] Critical service unavailable (blocks dependent operations)
- [ ] Backup not running (missed scheduled backup)
- [ ] Certificate expiry warning (30 days)
- [ ] High latency (p95 > threshold)

---

## Phase 3 — Log Quality

**Goal:** Audit structured logging for consistency, levels, and sensitive data.

### LLM steps

1. Read source files in `scope.source_dirs` to identify logging calls. The logging framework varies (tracing/log in Rust, logging/structlog in Python, winston/pino in Node, log4j/slf4j in Java, zap/zerolog in Go) but the quality criteria are universal.
2. Check that logs use structured format (key=value pairs or JSON) rather than free-form strings where possible.
3. Check that appropriate levels are used: DEBUG for internal state, INFO for lifecycle events, WARN for degraded-but-functional, ERROR for failures requiring attention.
4. Check that errors are not swallowed silently (catch blocks with no logging, empty error handlers).
5. Check that no sensitive data (passwords, tokens, PII) appears in log statements.

### Accelerator tools (optional)

```bash
# Rust — tracing / log crates
grep -rn 'info!\|warn!\|error!\|debug!\|trace!\|tracing::' \
  src/ --include='*.rs' | head -20

# Python — stdlib logging / structlog / loguru
grep -rn 'logging\.\|logger\.\|structlog\.\|loguru\.' \
  src/ --include='*.py' | head -20

# Node.js — winston / pino
grep -rn 'logger\.\|winston\.\|pino(' \
  src/ --include='*.js' --include='*.ts' | head -20

# Java — slf4j / log4j / logback
grep -rn 'log\.info\|log\.warn\|log\.error\|log\.debug\|LOGGER\.' \
  src/ --include='*.java' | head -20

# Go — zap / zerolog
grep -rn 'zap\.\|log\.Info\|log\.Error\|logger\.Info\|zerolog\.' \
  . --include='*.go' | head -20

# Sensitive data exposure across all languages
grep -rn 'password\|token\|secret\|bearer\|api_key\|apikey' src/ | \
  grep -iE 'info|warn|error|debug|log' | head -10
# Results here should be reviewed — confirm these are not logging raw values
```

### Checklist

- [ ] Structured logging used (key=value pairs or JSON, not free-form strings)
- [ ] JSON output format configured (for log aggregation)
- [ ] Log levels appropriate (no debug in hot paths for production)
- [ ] No sensitive data in log output (tokens, passwords, PII)
- [ ] Error logs include enough context (request ID, user context, error chain)
- [ ] Log rotation configured (prevent disk fill)

---

## Phase 4 — Dashboard Health

**Goal:** Verify dashboards reference real metrics and provide useful visibility.

### LLM steps

1. Read Grafana dashboard JSON files or equivalent dashboard config from the paths listed in `scope.dashboards`.
2. Verify that key metrics identified in Phase 1 have panels in at least one dashboard.
3. Check for stale panels referencing metrics that no longer exist in the codebase.

### Accelerator tools (optional)

```bash
# Locate dashboard JSON files
find config/ infra/ -name '*.json' -path '*grafana*' -path '*dashboard*' 2>/dev/null
find config/ infra/ -name '*.json' -path '*dashboard*' 2>/dev/null

# Metrics referenced by dashboards
for f in $(find config/ infra/ -name '*.json' -path '*dashboard*' 2>/dev/null); do
  echo "=== $(basename $f) ==="
  grep -oP '[a-z][a-z0-9_]+' "$f" | sort -u
done

# Cross-reference: are all dashboard metrics actually registered?
for f in $(find config/ infra/ -name '*.json' -path '*dashboard*' 2>/dev/null); do
  grep -oP '[a-z][a-z0-9_]+' "$f" | sort -u | while read metric; do
    grep -q "$metric" /tmp/code_metrics.txt 2>/dev/null || echo "MISSING_METRIC: $metric in $(basename $f)"
  done
done

# Count dashboards
find config/ infra/ -name '*.json' -path '*dashboard*' 2>/dev/null | wc -l
```

---

## Phase 5 — Health Endpoints

**Goal:** Verify health check implementation.

### LLM steps

1. Read source files in `scope.source_dirs` to identify health check endpoint implementations — look for routes or handlers named `health`, `healthz`, `readiness`, `liveness`, `ping`, or equivalent.
2. Verify the health check actually checks the health of dependencies (database connectivity, external service availability) rather than just returning a static 200 OK.
3. Verify the response format is machine-readable (JSON preferred) and includes status information.
4. Check that the health endpoint does not require authentication (it needs to be callable by orchestration infrastructure).

### Accelerator tools (optional)

```bash
# Rust — actix-web / axum / warp
grep -rn '"/health\|"/healthz\|"/readiness\|"/liveness\|health_handler\|healthcheck' \
  src/ --include='*.rs' | head -10

# Python — FastAPI / Flask / Django
grep -rn '@app.get.*health\|@router.get.*health\|@bp.route.*health\|url.*health' \
  src/ --include='*.py' | head -10

# Node.js — Express / Fastify / Koa
grep -rn "router\.get.*health\|app\.get.*health\|fastify\.get.*health" \
  src/ --include='*.js' --include='*.ts' | head -10

# Go — net/http / gin / chi
grep -rn 'HandleFunc.*health\|GET.*health\|r\.Get.*health' \
  . --include='*.go' | head -10

# Java — Spring Boot / Quarkus
grep -rn '@GetMapping.*health\|@RequestMapping.*health\|HealthIndicator' \
  src/ --include='*.java' | head -10

# Docker health check configuration
grep -A5 'healthcheck:' docker-compose.yml docker-compose*.yml 2>/dev/null
```

### Health Endpoint Checklist

- [ ] `/health` endpoint exists
- [ ] Returns structured response (JSON with component statuses)
- [ ] Checks database connectivity
- [ ] Checks dependent service reachability
- [ ] Returns appropriate HTTP status (200 healthy, 503 unhealthy)
- [ ] Does NOT leak sensitive information
- [ ] Does NOT require authentication
- [ ] Docker healthcheck configured for all services

---

## Phase 6 — Audit Trail

**Goal:** Verify security-relevant events are logged for forensics.

### LLM steps

1. Read source files handling user actions, authentication events, and data modifications from `scope.source_dirs`.
2. Verify that security-relevant events produce audit log entries: login/logout, permission changes, data exports, administrative actions.
3. Check that audit log entries include: who, what, when, outcome — these are universal fields regardless of language.
4. Verify that audit logs are separate from operational logs and cannot be silently dropped.

### Accelerator tools (optional)

```bash
# Generic audit log call patterns (adapt prefix to project convention)
grep -rn 'audit\|audit_log\|AuditLog\|audit_event\|AuditEvent' \
  src/ 2>/dev/null | head -20

# Rust
grep -rn 'audit!\|audit_log!\|audit::' src/ --include='*.rs' | head -10

# Python
grep -rn 'audit_log\.\|audit\.log\|AuditLogger\.' src/ --include='*.py' | head -10

# Node.js
grep -rn 'auditLog\.\|audit\.log\|auditLogger\.' \
  src/ --include='*.js' --include='*.ts' | head -10

# Java
grep -rn 'auditLog\.\|AuditLogger\.\|AuditService\.' src/ --include='*.java' | head -10

# Audit log retention config
grep -rn 'retention\|expire\|rotate\|cleanup.*audit' \
  src/ config/ --include='*.yaml' --include='*.toml' --include='*.json' | head -5
```

### Required Audit Events

- [ ] Authentication success/failure (who, when, how)
- [ ] Permission grants/revocations
- [ ] Access control escalation (action approval/rejection)
- [ ] Action blocked by access control (what, why)
- [ ] Configuration changes (personality/configuration files, access control config)
- [ ] Operations with sensitive data access
- [ ] Admin operations (backup, restore, DB maintenance)

---

## Output

Reports are written to `output/YYYY-MM-DD_{project_name}/OB{n}-observability-tomographe.md` (see `qualitoscope/config.yaml` for `project_name`).

---

## Configuration

This instrument reads project-specific paths from `project-profile.yaml` in the target project root. If a profile field is absent, the default from the profile schema applies. Instrument-specific thresholds remain in this instrument's `config.yaml`.

```yaml
thresholds:
  metrics:
    min_registered: 50
    docs_alignment_percent: 70
    naming_convention: "<project_prefix>_"
  alerting:
    min_alert_rules: 8
    required_alerts: [ServiceDown, HighMemoryUsage, DiskSpaceLow]
  logging:
    sensitive_data_in_logs: 0
    json_format_required: true
  dashboards:
    min_dashboards: 3
    orphan_metrics_max: 5
  health:
    endpoints_required: ["/health"]
    dependency_checks: [db]
  audit:
    required_events: [auth_success, auth_failure, action_blocked]

scope:
  source_dirs: []                        # list source directories to scan, e.g. [src/, lib/]
  metrics_source_dirs: []                # dirs containing metric registration; subset of source_dirs
  metrics_doc: docs/metrics-registry.md
  alert_rules: [config/prometheus/*.rules.yml, infra/prometheus/*.rules.yml]
  dashboards: [config/grafana/dashboards/, infra/grafana/dashboards/]
  compose_file: docker-compose.yml
```

---

## Run History

| Run | Date | Trigger | Report |
|-----|------|---------|--------|
| OB1 | _pending_ | Initial baseline | — |

## License

Part of [qual-gate](https://github.com/Nelvradia/qual-gate). Licensed under [Apache 2.0](../../LICENSE).
