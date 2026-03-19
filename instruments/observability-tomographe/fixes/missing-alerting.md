---
title: "Fix: Missing Alerting"
status: current
last-updated: 2026-03-19
instrument: observability-tomographe
severity-range: "Major"
---

# Fix: Missing Alerting

## What this means

Your service has metrics or logs but no alert rules to notify operators when things go wrong.
Without alerting, outages are detected by customers filing support tickets, not by your on-call
team responding to a page. Missing alerting is the gap between "we can see a dashboard" and "we
get woken up when the dashboard turns red." Even services with basic alerts often suffer from
poor alert design: alerts on symptoms instead of impact, missing SLO-based burn-rate alerts, no
runbook links in alert annotations, or alert storms that desensitise responders (alert fatigue).

## How to fix

### Step 1: Define your SLOs

Before writing alert rules, define what "working" means for your service. Service Level
Objectives quantify your reliability targets:

| SLI (indicator) | SLO (target) | Example |
|-----------------|--------------|---------|
| Availability | 99.9% of requests succeed | < 43.8 min downtime/month |
| Latency | 99% of requests < 500ms | p99 latency budget |
| Error rate | < 0.1% of requests return 5xx | Error budget per window |
| Freshness | Data updated within 60 seconds | Staleness threshold |

### Step 2: Write SLO-based burn-rate alerts

Burn-rate alerts fire when you are consuming your error budget faster than sustainable. They
replace naive threshold alerts (e.g., "error rate > 5%") that either fire too late for fast
incidents or too eagerly for brief spikes.

**Prometheus alerting rules (multi-window burn rate):**

```yaml
# prometheus/rules/slo-alerts.yml
groups:
  - name: slo_burn_rate
    rules:
      # Fast burn — 2% of monthly budget consumed in 1 hour
      # Fires within minutes of a major incident
      - alert: HighErrorBurnRate_Fast
        expr: |
          (
            sum(rate(http_requests_total{status=~"5.."}[5m]))
            /
            sum(rate(http_requests_total[5m]))
          ) > (14.4 * 0.001)
          and
          (
            sum(rate(http_requests_total{status=~"5.."}[1h]))
            /
            sum(rate(http_requests_total[1h]))
          ) > (14.4 * 0.001)
        for: 2m
        labels:
          severity: critical
          team: platform
        annotations:
          summary: "High error burn rate — 2% of monthly budget consumed in ~1h"
          description: >
            Service {{ $labels.job }} is burning error budget at 14.4x the
            sustainable rate. Current 5m error ratio: {{ $value | humanizePercentage }}.
          runbook: "https://runbooks.internal/slo/high-error-burn-rate"
          dashboard: "https://grafana.internal/d/slo-overview"

      # Slow burn — 10% of monthly budget consumed in 3 days
      # Catches chronic low-grade degradation
      - alert: HighErrorBurnRate_Slow
        expr: |
          (
            sum(rate(http_requests_total{status=~"5.."}[30m]))
            /
            sum(rate(http_requests_total[30m]))
          ) > (1.0 * 0.001)
          and
          (
            sum(rate(http_requests_total{status=~"5.."}[6h]))
            /
            sum(rate(http_requests_total[6h]))
          ) > (1.0 * 0.001)
        for: 15m
        labels:
          severity: warning
          team: platform
        annotations:
          summary: "Slow error burn rate — budget erosion over days"
          runbook: "https://runbooks.internal/slo/slow-error-burn-rate"

      # Latency SLO — p99 breaching target
      - alert: LatencySLOBreach
        expr: |
          histogram_quantile(0.99,
            sum(rate(http_request_duration_seconds_bucket[5m])) by (le, job)
          ) > 0.5
        for: 5m
        labels:
          severity: warning
          team: platform
        annotations:
          summary: "p99 latency exceeds 500ms SLO"
          description: >
            Service {{ $labels.job }} p99 latency is {{ $value }}s,
            exceeding the 500ms SLO target.
          runbook: "https://runbooks.internal/slo/latency-breach"
```

### Step 3: Add infrastructure and dependency alerts

```yaml
# prometheus/rules/infra-alerts.yml
groups:
  - name: infrastructure
    rules:
      - alert: TargetDown
        expr: up == 0
        for: 3m
        labels:
          severity: critical
        annotations:
          summary: "Scrape target {{ $labels.job }} is down"
          runbook: "https://runbooks.internal/infra/target-down"

      - alert: HighMemoryUsage
        expr: |
          (node_memory_MemTotal_bytes - node_memory_MemAvailable_bytes)
          / node_memory_MemTotal_bytes > 0.90
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "Memory usage above 90% for 10 minutes"
          runbook: "https://runbooks.internal/infra/high-memory"

      - alert: DiskSpaceRunningOut
        expr: |
          predict_linear(node_filesystem_avail_bytes[6h], 24*3600) < 0
        for: 30m
        labels:
          severity: warning
        annotations:
          summary: "Disk predicted to fill within 24 hours"
          runbook: "https://runbooks.internal/infra/disk-space"
```

### Step 4: Configure notification routing

**Alertmanager configuration:**

```yaml
# alertmanager/alertmanager.yml
global:
  resolve_timeout: 5m

route:
  receiver: default
  group_by: ["alertname", "job"]
  group_wait: 30s        # Wait before sending first notification
  group_interval: 5m     # Wait between notifications for same group
  repeat_interval: 4h    # Re-notify after silence period
  routes:
    - match:
        severity: critical
      receiver: pagerduty-critical
      continue: true      # Also send to Slack
    - match:
        severity: critical
      receiver: slack-critical
    - match:
        severity: warning
      receiver: slack-warning

receivers:
  - name: default
    slack_configs:
      - api_url: "${SLACK_WEBHOOK_URL}"
        channel: "#alerts-default"

  - name: pagerduty-critical
    pagerduty_configs:
      - service_key: "${PAGERDUTY_SERVICE_KEY}"
        description: "{{ .CommonAnnotations.summary }}"
        details:
          runbook: "{{ .CommonAnnotations.runbook }}"

  - name: slack-critical
    slack_configs:
      - api_url: "${SLACK_WEBHOOK_URL}"
        channel: "#alerts-critical"
        title: "[CRITICAL] {{ .CommonLabels.alertname }}"
        text: "{{ .CommonAnnotations.description }}\nRunbook: {{ .CommonAnnotations.runbook }}"
        send_resolved: true

  - name: slack-warning
    slack_configs:
      - api_url: "${SLACK_WEBHOOK_URL}"
        channel: "#alerts-warning"
        send_resolved: true
```

### General

**Alert design principles:**

- **Alert on impact, not cause.** Alert on "error rate exceeding SLO budget" not "CPU at 80%."
  High CPU with happy users is not an incident.
- **Every alert must be actionable.** If the responder cannot do anything, it is not an alert —
  it is a log line or a dashboard annotation.
- **Every alert must have a runbook.** The runbook answers: What does this alert mean? What
  should I check first? How do I mitigate? When should I escalate?
- **Two severity levels are enough.** Critical = page someone now (service is impacting users).
  Warning = investigate during business hours (budget erosion, capacity concern).
- **Tune aggressively.** An alert that fires and gets ignored is worse than no alert — it trains
  the team to ignore pages.

**Avoiding alert fatigue:**

- Group related alerts. Five alerts about the same incident should arrive as one notification.
- Use `for:` duration to avoid flapping. A 2-minute spike that self-resolves is not page-worthy.
- Review alert frequency monthly. Any alert that fires > 5 times/week without action needs
  tuning, auto-remediation, or deletion.
- Separate critical (page) from warning (ticket/Slack). Never page for warnings.
- Implement alert silences during planned maintenance.

**Escalation path template:**

```
1. Alert fires → on-call engineer paged (PagerDuty/OpsGenie)
2. No acknowledgement in 5 min → escalate to secondary on-call
3. No acknowledgement in 15 min → escalate to engineering manager
4. Incident declared → create incident channel, notify stakeholders
5. Post-incident → blameless review within 48 hours
```

**Runbook template (minimum viable):**

```markdown
# Alert: {AlertName}

## What is this?
{One sentence: what the alert detects and why it matters.}

## Impact
{Who is affected? What user-facing behaviour degrades?}

## First response
1. Check {dashboard link} for current state.
2. Check {log query link} for error details.
3. {Specific diagnostic command or query.}

## Mitigation
- {Immediate action to reduce impact — rollback, scale up, failover.}

## Escalation
- If unresolved after 30 min, escalate to {team/person}.
- If data loss suspected, notify {compliance/leadership}.
```

## Prevention

**CI validation of alert rules:**

```yaml
# GitLab CI — validate Prometheus rules syntax
alert-lint:
  stage: lint
  image: prom/prometheus:latest
  script:
    - promtool check rules prometheus/rules/*.yml
  allow_failure: false
```

**Alert coverage audit:**

- Maintain a service catalogue that maps each service to its SLOs and corresponding alerts.
- During quarterly reviews, verify every production service has at least: one availability
  alert, one latency alert, and one dependency-health alert.
- Use `amtool` (Alertmanager CLI) to test alert routing: `amtool config routes test
  --config.file=alertmanager.yml severity=critical team=platform`.

**Runbook enforcement:**

- Reject alert rules in code review if the `runbook` annotation is missing or points to a
  non-existent URL.
- CI check: parse alert YAML, extract runbook URLs, verify they return HTTP 200.

**On-call hygiene:**

- Track alert volume per week. Set a target: < 2 pages per on-call shift outside business hours.
- Every alert that fires must result in one of: action taken, alert tuned, or alert deleted.
  "Ignored" is not an acceptable outcome.
