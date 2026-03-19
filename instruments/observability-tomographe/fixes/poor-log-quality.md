---
title: "Fix: Poor Log Quality"
status: current
last-updated: 2026-03-19
instrument: observability-tomographe
severity-range: "Minor–Major"
---

# Fix: Poor Log Quality

## What this means

Your service logs are unstructured (plain text without machine-parseable fields), use inconsistent
or incorrect log levels, lack correlation IDs for tracing requests across components, or contain
sensitive data (passwords, tokens, PII). Poor log quality makes incident response slower — you
cannot filter, aggregate, or search logs efficiently. Unstructured logs break log aggregation
pipelines (ELK, Loki, Datadog). Missing correlation IDs make it impossible to reconstruct a
request's path through a distributed system. Sensitive data in logs creates compliance violations
(GDPR, HIPAA) and security risks if log storage is compromised.

## How to fix

### Python

**Use structlog for structured, levelled logging:**

```python
# requirements.txt or pyproject.toml
# structlog >= 24.0

import logging
import structlog
import uuid

def configure_logging() -> None:
    """Configure structured logging. Call once at application startup."""
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
    )


def create_request_logger(request_id: str | None = None) -> structlog.BoundLogger:
    """Create a logger bound with a correlation ID."""
    correlation_id = request_id or str(uuid.uuid4())
    return structlog.get_logger().bind(correlation_id=correlation_id)


# Usage
log = create_request_logger("req-abc-123")
log.info("order_processed", order_id="ORD-456", items=3, total_cents=4999)
# Output: {"correlation_id": "req-abc-123", "event": "order_processed",
#          "order_id": "ORD-456", "items": 3, "total_cents": 4999,
#          "level": "info", "timestamp": "2026-03-19T10:30:00Z"}

# Correct log levels
log.debug("cache_lookup", key="user:42")           # Internal state
log.info("server_started", port=8080)               # Lifecycle events
log.warning("pool_saturation", active=48, max=50)   # Degraded but functional
log.error("payment_failed", provider="stripe", error_code="card_declined")
```

**Redact sensitive fields:**

```python
import structlog
import re

SENSITIVE_PATTERNS = re.compile(
    r"(password|token|secret|api_key|authorization|ssn|credit_card)",
    re.IGNORECASE,
)

def redact_sensitive(
    logger: structlog.types.WrappedLogger,
    method_name: str,
    event_dict: dict,
) -> dict:
    """Processor that redacts sensitive values from log events."""
    for key in list(event_dict.keys()):
        if SENSITIVE_PATTERNS.search(key):
            event_dict[key] = "***REDACTED***"
    return event_dict

# Add to structlog processors list before JSONRenderer:
# redact_sensitive,
```

### Rust

**Use the `tracing` crate with structured spans:**

```rust
// Cargo.toml
// [dependencies]
// tracing = "0.1"
// tracing-subscriber = { version = "0.3", features = ["json", "env-filter"] }
// uuid = { version = "1", features = ["v4"] }

use tracing::{info, warn, error, instrument, Span};
use tracing_subscriber::{fmt, EnvFilter};

fn init_logging() {
    tracing_subscriber::fmt()
        .json()                              // Structured JSON output
        .with_env_filter(EnvFilter::from_default_env()) // RUST_LOG=info
        .with_target(true)
        .with_thread_ids(true)
        .init();
}

// The #[instrument] macro automatically creates a span with function args
#[instrument(skip(password), fields(correlation_id = %correlation_id))]
fn process_login(username: &str, password: &str, correlation_id: &str) {
    info!(username = %username, "login_attempt_started");

    // ... authentication logic ...

    if auth_failed {
        warn!(username = %username, reason = "invalid_credentials",
              "login_attempt_failed");
    } else {
        info!(username = %username, "login_attempt_succeeded");
    }
}

// Propagate correlation IDs across async boundaries
#[instrument(fields(correlation_id = %req_id))]
async fn handle_request(req_id: String) {
    info!("request_received");
    // All logs within this span automatically include correlation_id
    process_order().await;
}
```

### TypeScript

**Use pino for high-performance structured logging:**

```typescript
// package.json: "pino": "^9.0"

import pino from "pino";
import { randomUUID } from "crypto";

// Configure structured logger
const logger = pino({
  level: process.env.LOG_LEVEL ?? "info",
  timestamp: pino.stdTimeFunctions.isoTime,
  formatters: {
    level(label: string) {
      return { level: label };
    },
  },
  redact: {
    paths: ["password", "token", "secret", "*.password", "*.token"],
    censor: "***REDACTED***",
  },
});

// Create child logger with correlation ID
function createRequestLogger(requestId?: string): pino.Logger {
  return logger.child({
    correlationId: requestId ?? randomUUID(),
  });
}

// Usage
const log = createRequestLogger("req-abc-123");
log.info({ orderId: "ORD-456", items: 3 }, "order_processed");
log.warn({ active: 48, max: 50 }, "pool_saturation");
log.error({ provider: "stripe", errorCode: "card_declined" }, "payment_failed");
```

### Go

**Use zerolog for zero-allocation structured logging:**

```go
package main

import (
    "os"
    "time"

    "github.com/google/uuid"
    "github.com/rs/zerolog"
    "github.com/rs/zerolog/log"
)

func initLogging() {
    zerolog.TimeFieldFormat = time.RFC3339
    zerolog.SetGlobalLevel(zerolog.InfoLevel)

    // JSON output for production, pretty console for development
    if os.Getenv("ENV") == "development" {
        log.Logger = log.Output(zerolog.ConsoleWriter{Out: os.Stderr})
    }
}

func createRequestLogger(correlationID string) zerolog.Logger {
    if correlationID == "" {
        correlationID = uuid.New().String()
    }
    return log.With().Str("correlation_id", correlationID).Logger()
}

func handleOrder(correlationID string) {
    reqLog := createRequestLogger(correlationID)

    reqLog.Info().
        Str("order_id", "ORD-456").
        Int("items", 3).
        Int("total_cents", 4999).
        Msg("order_processed")

    reqLog.Warn().
        Int("active", 48).
        Int("max", 50).
        Msg("pool_saturation")
}
```

### General

**Log level guidelines:**

| Level | Use for | Example |
|-------|---------|---------|
| DEBUG | Internal state, variable values, flow tracing | `cache_lookup key=user:42 hit=true` |
| INFO  | Lifecycle events, successful operations | `server_started port=8080` |
| WARN  | Degraded but functional, approaching limits | `pool_near_capacity active=48 max=50` |
| ERROR | Failures requiring attention | `payment_failed provider=stripe` |
| FATAL | Unrecoverable, process will exit | `database_unreachable after retries=3` |

**Correlation ID propagation:**

- Generate a correlation ID at the system boundary (API gateway, message consumer).
- Pass it in HTTP headers (`X-Correlation-ID`), message metadata, or gRPC metadata.
- Every service in the chain logs with the same correlation ID.
- If your service fans out to multiple downstream calls, create child IDs:
  `req-abc-123` -> `req-abc-123.1`, `req-abc-123.2`.

**What never belongs in logs:**

- Passwords, tokens, API keys, secrets of any kind.
- Full credit card numbers, SSNs, or government IDs.
- Email addresses or personal data unless required and compliant with your privacy policy.
- Request/response bodies containing user-submitted data (log a hash or truncated form).

## Prevention

**CI enforcement of structured logging:**

```yaml
# GitLab CI — detect print statements and raw logging
log-lint:
  stage: lint
  script:
    - |
      # Python: reject bare print() in src/
      if grep -rn "^\s*print(" src/ --include="*.py" | grep -v "# noqa"; then
        echo "ERROR: Use structlog instead of print()"
        exit 1
      fi
      # Reject logging.basicConfig (forces unstructured output)
      if grep -rn "logging.basicConfig" src/ --include="*.py"; then
        echo "ERROR: Use structlog configuration instead of basicConfig"
        exit 1
      fi
  allow_failure: false
```

**Log aggregation pipeline validation:**

- Parse a sample of logs in CI to verify they are valid JSON. A single unstructured log line
  can break downstream parsing.
- Include a `log_format_test` that emits each log level and asserts the output is valid JSON
  with required fields (`timestamp`, `level`, `event`/`msg`, `correlation_id`).

**Review checklist:**

- Every log statement uses structured key-value pairs, not string interpolation.
- Log levels match the severity guidelines above.
- No sensitive data in log values — check for fields named password, token, secret, key.
- Correlation ID is bound to the logger at request entry and propagated to all downstream calls.
- Error logs include enough context to diagnose without guessing (error type, relevant IDs,
  what operation was attempted).
