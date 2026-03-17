# observability-tomographe/

**Observability health scanner.** Audits Prometheus metrics coverage, alerting rules, log quality, Grafana dashboards, health endpoints, and audit trail completeness.

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
| **2** | Alerting Rules | Validate Prometheus alert rules, thresholds, routing | No |
| **3** | Log Quality | Audit structured logging format, levels, sensitive data | No |
| **4** | Dashboard Health | Validate Grafana dashboards reference real metrics | No (reads JSON) |
| **5** | Health Endpoints | Verify health check implementation and response format | Partial |
| **6** | Audit Trail | Verify access control decisions, security events are logged | No |
| **7** | Report | Compile findings | No |

---

## Phase 1 — Metrics Coverage

**Goal:** Verify that all documented metrics are actually registered in code, and all registered metrics are documented.

```bash
# Metrics registered in code
grep -rn 'register\|counter!\|histogram!\|gauge!\|IntCounter\|Histogram\|Gauge' \
  src/ --include='*.rs' --include='*.py' 2>/dev/null | \
  grep -oP '[a-z]+_[a-z_]+' | sort -u > /tmp/code_metrics.txt
echo "Metrics in code: $(wc -l < /tmp/code_metrics.txt)"

# Metrics documented in metrics registry
grep -oP '[a-z]+_[a-z_]+' docs/metrics-registry.md 2>/dev/null | \
  sort -u > /tmp/doc_metrics.txt
echo "Metrics in docs: $(wc -l < /tmp/doc_metrics.txt)"

# Missing from code (documented but not registered)
comm -23 /tmp/doc_metrics.txt /tmp/code_metrics.txt > /tmp/missing_from_code.txt
echo "Documented but not in code: $(wc -l < /tmp/missing_from_code.txt)"
cat /tmp/missing_from_code.txt

# Missing from docs (registered but not documented)
comm -13 /tmp/doc_metrics.txt /tmp/code_metrics.txt > /tmp/missing_from_docs.txt
echo "In code but not documented: $(wc -l < /tmp/missing_from_docs.txt)"
cat /tmp/missing_from_docs.txt

# Metric naming convention (should follow a consistent prefix)
grep -rn 'register\|counter!\|histogram!\|gauge!' src/ --include='*.rs' --include='*.py' | head -10

# Metric labels consistency
grep -rn 'label_names\|with_label_values\|.labels(' src/ --include='*.rs' --include='*.py' | head -20
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

**Goal:** Validate Prometheus alerting rules are correct and useful.

```bash
# Alert rules file existence
find config/ infra/ -name '*.rules.yml' -o -name 'alerts.yml' -o -name '*.rules' 2>/dev/null

# Validate with promtool (if available)
for f in $(find config/ infra/ -name '*.rules.yml' -o -name '*.rules' 2>/dev/null); do
  promtool check rules "$f" 2>&1 || echo "PROMTOOL_UNAVAILABLE: manual review needed for $f"
done

# Count alert rules
grep -c 'alert:' config/prometheus/*.rules.yml infra/prometheus/*.rules.yml 2>/dev/null

# Critical alerts that should exist (adapt to your service names)
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

```bash
# Logging framework
grep -rn 'tracing\|log::\|slog\|env_logger\|logging\|loguru' \
  Cargo.toml pyproject.toml requirements.txt 2>/dev/null

# Structured fields in log statements
grep -rn 'tracing::\|info!\|warn!\|error!\|debug!\|trace!\|logging\.' src/ --include='*.rs' --include='*.py' | head -20
# Look for structured fields (key = value) vs unstructured strings

# Log level distribution
for level in trace debug info warn error; do
  count=$(grep -rn "${level}!\|${level}(" src/ --include='*.rs' --include='*.py' 2>/dev/null | wc -l)
  echo "$level: $count"
done

# Sensitive data in logs (should NOT appear)
grep -rn 'password\|token\|secret\|bearer\|key=' src/ --include='*.rs' --include='*.py' | \
  grep -E 'info!|warn!|error!|debug!|logging\.' | head -10
# These should be redacted or absent

# Error context (errors should include enough context to debug)
grep -A2 'error!' src/ --include='*.rs' -r | head -30

# Log output format (JSON recommended for parsing)
grep -rn 'json\|Json\|fmt.*json\|subscriber.*json' src/ --include='*.rs' --include='*.py' | head -5
```

### Checklist

- [ ] Structured logging used (e.g., tracing crate, structured Python logging)
- [ ] JSON output format configured (for log aggregation)
- [ ] Log levels appropriate (no debug in hot paths for production)
- [ ] No sensitive data in log output (tokens, passwords, PII)
- [ ] Error logs include enough context (request ID, user context, error chain)
- [ ] Log rotation configured (prevent disk fill)

---

## Phase 4 — Dashboard Health

**Goal:** Verify Grafana dashboards reference real metrics and provide useful visibility.

```bash
# Dashboard JSON files
find config/ infra/ -name '*.json' -path '*grafana*' -path '*dashboard*' 2>/dev/null
find config/ infra/ -name '*.json' -path '*dashboard*' 2>/dev/null

# Metrics referenced by dashboards
for f in $(find config/ infra/ -name '*.json' -path '*dashboard*' 2>/dev/null); do
  echo "=== $(basename $f) ==="
  grep -oP '[a-z]+_[a-z_]+' "$f" | sort -u
done

# Dashboards vs available metrics
# Cross-reference: are all dashboard metrics actually registered?
for f in $(find config/ infra/ -name '*.json' -path '*dashboard*' 2>/dev/null); do
  grep -oP '[a-z]+_[a-z_]+' "$f" | sort -u | while read metric; do
    grep -q "$metric" /tmp/code_metrics.txt 2>/dev/null || echo "MISSING_METRIC: $metric in $(basename $f)"
  done
done

# Count dashboards
find config/ infra/ -name '*.json' -path '*dashboard*' 2>/dev/null | wc -l
```

---

## Phase 5 — Health Endpoints

**Goal:** Verify health check implementation.

```bash
# Health endpoint implementation
grep -rn 'health\|Health\|/health\|healthcheck' src/ --include='*.rs' --include='*.py' | head -10

# What the health check returns
grep -A20 'health' src/ --include='*.rs' --include='*.py' -r | head -30

# Docker health checks
grep -A5 'healthcheck:' docker-compose.yml 2>/dev/null

# Does health check verify dependencies?
# Should check: DB accessible, dependent services reachable
grep -rn 'db.*health\|service.*health\|check.*connection' src/ --include='*.rs' --include='*.py' | head -10
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

```bash
# Access control decision logging
grep -rn 'audit\|decision.*log\|enforce.*log\|action.*log' src/ --include='*.rs' --include='*.py' | head -10

# Events that should be logged:
for event in "auth_success" "auth_failure" "permission_grant" "permission_revoke" "action_blocked" "action_approved" "config_change"; do
  found=$(grep -rn "$event\|$(echo $event | tr '_' '.')" src/ --include='*.rs' --include='*.py' 2>/dev/null | wc -l)
  echo "$event: $found references"
done

# Audit log persistence
grep -rn 'audit' src/ --include='*.rs' --include='*.py' --include='*.sql' | head -10
# Should have a dedicated audit table or log file

# Audit log retention
grep -rn 'retention\|expire\|rotate\|cleanup.*audit' src/ config/ --include='*.rs' --include='*.py' --include='*.yaml' | head -5
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

Reports are written to `output/YYYY-MM-DD/OB<N>-observability-tomographe.md`.

---

## Configuration

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
  metrics_file: src/metrics.rs
  metrics_doc: docs/metrics-registry.md
  alert_rules: [config/prometheus/*.rules.yml, infra/prometheus/*.rules.yml]
  dashboards: [config/grafana/dashboards/, infra/grafana/dashboards/]
  compose_file: docker-compose.yml
  api_dir: src/api/
```

---

## Run History

| Run | Date | Trigger | Report |
|-----|------|---------|--------|
| OB1 | _pending_ | Initial baseline | — |

## License

Part of [qual-gate](https://github.com/Nelvradia/qual-gate). Licensed under [Apache 2.0](../../LICENSE).
