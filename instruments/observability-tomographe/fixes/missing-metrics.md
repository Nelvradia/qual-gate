---
title: "Fix: Missing Metrics"
status: current
last-updated: 2026-03-19
instrument: observability-tomographe
severity-range: "Major"
---

# Fix: Missing Metrics

## What this means

Your service exposes no application-level metrics, or the metrics it exposes are insufficient to
answer basic operational questions: Is the service healthy? How much traffic is it handling? Where
is time being spent? Without metrics, you are flying blind — outages are detected by users instead
of dashboards, capacity planning is guesswork, and incident response depends on log archaeology
rather than real-time signals. The RED method (Rate, Errors, Duration) for request-driven services
and the USE method (Utilisation, Saturation, Errors) for resource-oriented components provide a
minimum viable set of metrics every service should expose.

## How to fix

### Python

**Install prometheus-client and expose RED metrics:**

```python
# requirements.txt or pyproject.toml
# prometheus-client >= 0.20

from prometheus_client import Counter, Histogram, Gauge, start_http_server

# RED metrics for a request-driven service
REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total HTTP requests",
    labelnames=["method", "endpoint", "status"],
)
REQUEST_DURATION = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency in seconds",
    labelnames=["method", "endpoint"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)
IN_PROGRESS = Gauge(
    "http_requests_in_progress",
    "Number of HTTP requests currently being processed",
    labelnames=["method"],
)

# USE metrics for a resource (e.g., connection pool, worker pool)
POOL_UTILISATION = Gauge(
    "pool_connections_active",
    "Number of active connections in the pool",
)
POOL_SIZE = Gauge(
    "pool_connections_max",
    "Maximum number of connections in the pool",
)
POOL_ERRORS = Counter(
    "pool_connection_errors_total",
    "Total connection errors from the pool",
    labelnames=["error_type"],
)


def handle_request(method: str, endpoint: str) -> None:
    IN_PROGRESS.labels(method=method).inc()
    with REQUEST_DURATION.labels(method=method, endpoint=endpoint).time():
        try:
            # ... actual request handling ...
            status = "200"
        except Exception:
            status = "500"
            raise
        finally:
            REQUEST_COUNT.labels(
                method=method, endpoint=endpoint, status=status
            ).inc()
            IN_PROGRESS.labels(method=method).dec()


if __name__ == "__main__":
    start_http_server(9090)  # Expose /metrics on port 9090
```

### Rust

**Use the `metrics` and `metrics-exporter-prometheus` crates:**

```rust
// Cargo.toml
// [dependencies]
// metrics = "0.23"
// metrics-exporter-prometheus = "0.15"

use metrics::{counter, gauge, histogram};
use metrics_exporter_prometheus::PrometheusBuilder;

fn init_metrics() {
    // Starts a Prometheus scrape endpoint on 0.0.0.0:9090
    PrometheusBuilder::new()
        .with_http_listener(([0, 0, 0, 0], 9090))
        .install()
        .expect("failed to install Prometheus exporter");
}

fn handle_request(method: &str, endpoint: &str) {
    let start = std::time::Instant::now();

    // ... actual request handling ...

    let duration = start.elapsed().as_secs_f64();
    counter!("http_requests_total", "method" => method.to_string(),
        "endpoint" => endpoint.to_string(), "status" => "200").increment(1);
    histogram!("http_request_duration_seconds", "method" => method.to_string(),
        "endpoint" => endpoint.to_string()).record(duration);
}
```

### TypeScript

**Use prom-client with Express:**

```typescript
import express from "express";
import client from "prom-client";

// Collect default Node.js metrics (GC, event loop, memory)
client.collectDefaultMetrics();

// RED metrics
const httpRequestsTotal = new client.Counter({
  name: "http_requests_total",
  help: "Total HTTP requests",
  labelNames: ["method", "route", "status"] as const,
});

const httpRequestDuration = new client.Histogram({
  name: "http_request_duration_seconds",
  help: "HTTP request latency in seconds",
  labelNames: ["method", "route"] as const,
  buckets: [0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0],
});

// Middleware to instrument all routes
function metricsMiddleware(
  req: express.Request,
  res: express.Response,
  next: express.NextFunction
): void {
  const end = httpRequestDuration.startTimer({
    method: req.method,
    route: req.route?.path ?? req.path,
  });
  res.on("finish", () => {
    end();
    httpRequestsTotal.inc({
      method: req.method,
      route: req.route?.path ?? req.path,
      status: String(res.statusCode),
    });
  });
  next();
}

const app = express();
app.use(metricsMiddleware);
app.get("/metrics", async (_req, res) => {
  res.set("Content-Type", client.register.contentType);
  res.end(await client.register.metrics());
});
```

### Go

**Use the official prometheus/client_golang:**

```go
package main

import (
    "net/http"
    "time"

    "github.com/prometheus/client_golang/prometheus"
    "github.com/prometheus/client_golang/prometheus/promauto"
    "github.com/prometheus/client_golang/prometheus/promhttp"
)

var (
    httpRequestsTotal = promauto.NewCounterVec(
        prometheus.CounterOpts{
            Name: "http_requests_total",
            Help: "Total HTTP requests",
        },
        []string{"method", "endpoint", "status"},
    )
    httpRequestDuration = promauto.NewHistogramVec(
        prometheus.HistogramOpts{
            Name:    "http_request_duration_seconds",
            Help:    "HTTP request latency in seconds",
            Buckets: prometheus.DefBuckets,
        },
        []string{"method", "endpoint"},
    )
)

func instrumentHandler(next http.Handler) http.Handler {
    return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
        start := time.Now()
        recorder := &statusRecorder{ResponseWriter: w, statusCode: 200}
        next.ServeHTTP(recorder, r)
        duration := time.Since(start).Seconds()

        httpRequestsTotal.WithLabelValues(
            r.Method, r.URL.Path, http.StatusText(recorder.statusCode),
        ).Inc()
        httpRequestDuration.WithLabelValues(
            r.Method, r.URL.Path,
        ).Observe(duration)
    })
}

func main() {
    http.Handle("/metrics", promhttp.Handler())
    // Wrap your routes with instrumentHandler(...)
}
```

### General

**RED method (request-driven services):**

- **Rate:** Requests per second (`http_requests_total`).
- **Errors:** Failed requests per second, by error type/code.
- **Duration:** Latency distribution, not just average. Use histograms with meaningful bucket
  boundaries aligned to your SLO (e.g., p99 < 500ms means you need buckets around that range).

**USE method (resources — pools, queues, CPUs, disks):**

- **Utilisation:** Proportion of resource in use (e.g., 80% of connection pool consumed).
- **Saturation:** Work waiting to be served (e.g., queue depth, thread pool backlog).
- **Errors:** Resource-level failures (e.g., connection refused, disk write error).

**Naming conventions (Prometheus):**

- Use snake_case. Suffix counters with `_total`, histograms with the unit (`_seconds`,
  `_bytes`). Gauges get no suffix.
- Keep label cardinality low. Never use user IDs, request IDs, or unbounded values as labels —
  this causes metric explosion and OOM in Prometheus.

**Metric endpoint requirements:**

- Expose metrics on a separate port or `/metrics` path.
- Respond in < 1 second — if metric collection is slow, you have a bug in your instrumentation.
- Include a `up` or health gauge that Prometheus can use for target health checks.

## Prevention

**CI checks for metric coverage:**

```yaml
# GitLab CI — verify at least one metric is registered
metric-coverage:
  stage: lint
  script:
    - |
      # Python: check for prometheus_client usage
      if find . -name "*.py" | head -1 > /dev/null 2>&1; then
        grep -rn "prometheus_client\|Counter\|Histogram\|Gauge" src/ \
          || (echo "ERROR: No Prometheus metrics found in src/" && exit 1)
      fi
  allow_failure: false
```

**Dashboard-as-code (Grafana provisioning):**

- Store dashboard JSON in the repo under `dashboards/`. Deploy with Grafana provisioning or
  the Grafana HTTP API in CI.
- Every service must have a RED dashboard created before the service reaches production.

**Review checklist:**

- Every new endpoint or background job must expose at least Rate and Duration metrics.
- Every new resource pool (DB connections, thread pool, cache) must expose USE metrics.
- Label names reviewed for cardinality — reject labels that can exceed ~100 unique values.
- Histogram buckets aligned to the service's SLO targets.
