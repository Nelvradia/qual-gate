---
title: "Fix: Missing Connection Pooling"
status: current
last-updated: 2026-03-19
instrument: performance-tomographe
severity-range: "Major"
---

# Fix: Missing Connection Pooling

## What this means

Your service creates a new connection to an external resource (database, cache, HTTP API, message
broker) for every request or operation, instead of reusing connections from a pool. Connection
establishment is expensive — a PostgreSQL connection involves TCP handshake, TLS negotiation, and
authentication, typically taking 20-100ms. Under load, this per-request overhead accumulates:
100 requests/second without pooling means 100 connection setups per second, consuming server and
database resources. Eventually the database hits its max connection limit, new connections are
refused, and the service fails. Connection pooling amortises this cost by maintaining a set of
pre-established, reusable connections.

## How to fix

### Python

**SQLAlchemy connection pool (relational databases):**

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

# Engine manages the connection pool — create ONCE at application startup
engine = create_engine(
    "postgresql+psycopg://user:pass@db-host:5432/mydb",
    pool_size=10,           # Steady-state connections kept open
    max_overflow=5,         # Extra connections allowed during spikes
    pool_timeout=30,        # Seconds to wait for a connection before error
    pool_recycle=1800,      # Recycle connections after 30 min (avoid stale)
    pool_pre_ping=True,     # Verify connection health before checkout
    echo_pool="debug",      # Log pool events (disable in production)
)


def handle_request() -> None:
    with Session(engine) as session:
        # Connection checked out from pool automatically
        result = session.execute(...)
        session.commit()
    # Connection returned to pool when context manager exits
```

**httpx connection pool (HTTP clients):**

```python
import httpx

# Create a client with connection pooling — reuse across requests
http_client = httpx.Client(
    limits=httpx.Limits(
        max_connections=50,           # Total pool size
        max_keepalive_connections=20, # Idle connections to keep
        keepalive_expiry=30,          # Seconds before idle connection closes
    ),
    timeout=httpx.Timeout(10.0),
)

# Async variant
async_client = httpx.AsyncClient(
    limits=httpx.Limits(max_connections=50, max_keepalive_connections=20),
    timeout=httpx.Timeout(10.0),
)


# Use the shared client — NOT httpx.get() which creates a new connection
def call_api(url: str) -> dict:
    response = http_client.get(url)
    response.raise_for_status()
    return response.json()
```

**Redis connection pool:**

```python
import redis

# Pool created once at startup
pool = redis.ConnectionPool(
    host="redis-host",
    port=6379,
    max_connections=20,
    socket_timeout=5,
    socket_connect_timeout=5,
    health_check_interval=30,
)
redis_client = redis.Redis(connection_pool=pool)
```

### Rust

**Use `deadpool` or `bb8` for async connection pooling:**

```rust
// Cargo.toml
// [dependencies]
// deadpool-postgres = "0.14"
// tokio-postgres = "0.7"

use deadpool_postgres::{Config, Pool, Runtime};
use tokio_postgres::NoTls;

fn create_pool() -> Pool {
    let mut cfg = Config::new();
    cfg.host = Some("db-host".to_string());
    cfg.port = Some(5432);
    cfg.dbname = Some("mydb".to_string());
    cfg.user = Some("user".to_string());
    cfg.password = Some("pass".to_string());

    cfg.pool = Some(deadpool_postgres::PoolConfig {
        max_size: 16,              // Maximum connections in pool
        timeouts: deadpool::managed::Timeouts {
            wait: Some(std::time::Duration::from_secs(30)),
            create: Some(std::time::Duration::from_secs(5)),
            recycle: Some(std::time::Duration::from_secs(5)),
        },
        ..Default::default()
    });

    cfg.create_pool(Some(Runtime::Tokio1), NoTls)
        .expect("failed to create connection pool")
}

async fn handle_request(pool: &Pool) -> Result<(), Box<dyn std::error::Error>> {
    let client = pool.get().await?;  // Checkout from pool
    let rows = client.query("SELECT id, name FROM users", &[]).await?;
    // Connection returned to pool when `client` is dropped
    Ok(())
}
```

**`reqwest` HTTP client with built-in pooling:**

```rust
use reqwest::Client;
use std::time::Duration;

// Create ONCE, reuse across requests. reqwest::Client pools connections.
fn create_http_client() -> Client {
    Client::builder()
        .pool_max_idle_per_host(20)          // Idle connections per host
        .pool_idle_timeout(Duration::from_secs(60))
        .connect_timeout(Duration::from_secs(5))
        .timeout(Duration::from_secs(30))
        .build()
        .expect("failed to create HTTP client")
}
```

### TypeScript

**`pg` (node-postgres) connection pool:**

```typescript
import { Pool } from "pg";

// Create pool ONCE at startup — not per request
const pool = new Pool({
  host: "db-host",
  port: 5432,
  database: "mydb",
  user: "user",
  password: "pass",
  max: 20,                   // Maximum connections in pool
  idleTimeoutMillis: 30_000, // Close idle connections after 30s
  connectionTimeoutMillis: 5_000, // Error if connection takes > 5s
});

// Health check on pool events
pool.on("error", (err) => {
  console.error("Unexpected pool error", err);
});

async function handleRequest(): Promise<void> {
  const client = await pool.connect(); // Checkout from pool
  try {
    const result = await client.query("SELECT id, name FROM users");
    // ... process result ...
  } finally {
    client.release(); // Return to pool — ALWAYS in a finally block
  }
}

// Or use pool.query() for single-statement queries (auto checkout/release):
async function getUser(id: number): Promise<User> {
  const { rows } = await pool.query("SELECT * FROM users WHERE id = $1", [id]);
  return rows[0];
}
```

### Go

**`database/sql` has built-in pooling — configure it:**

```go
package main

import (
    "database/sql"
    "time"

    _ "github.com/lib/pq"
)

func createPool() (*sql.DB, error) {
    db, err := sql.Open("postgres",
        "host=db-host port=5432 dbname=mydb user=user password=pass sslmode=require")
    if err != nil {
        return nil, err
    }

    // Configure pool parameters — the defaults are often too conservative
    db.SetMaxOpenConns(25)                 // Max total connections
    db.SetMaxIdleConns(10)                 // Max idle connections to keep
    db.SetConnMaxLifetime(30 * time.Minute) // Recycle connections periodically
    db.SetConnMaxIdleTime(5 * time.Minute)  // Close idle connections after 5 min

    // Verify connectivity
    if err := db.Ping(); err != nil {
        db.Close()
        return nil, err
    }
    return db, nil
}
```

### General

**Pool sizing guidelines:**

The optimal pool size depends on the backend's capacity and your service's concurrency. A common
starting formula for database connection pools:

```
pool_size = (2 * num_cpu_cores) + number_of_disks
```

For most cloud databases, start with 10-20 connections and adjust based on monitoring. Too many
connections waste database memory (each PostgreSQL connection uses ~10 MB). Too few cause request
queuing.

**Key principles:**

- **Create the pool once at startup**, not per request. Store it as application-level state
  (singleton, dependency injection, or global in simple services).
- **Always return connections to the pool.** Use try/finally, context managers, RAII, or defer.
  A leaked connection is worse than no pooling — it drains the pool silently.
- **Enable health checks.** Stale connections (closed by the server, network timeout) cause
  errors on first use. Pre-ping or background health checks catch these.
- **Set a connection timeout.** Waiting indefinitely for a connection during a traffic spike
  cascades into request timeouts. Fail fast with a clear error.
- **Monitor pool metrics.** Track: active connections, idle connections, wait time, checkout
  errors. Alert when the pool is consistently > 80% utilised.

## Prevention

**Detect missing pooling in code review:**

- Flag any code that creates a database connection, HTTP client, or Redis client inside a
  request handler or loop body.
- Flag `requests.get()` / `httpx.get()` (module-level convenience functions that create a new
  connection each call) — require a shared `Client` instance.

**CI monitoring of connection counts:**

```yaml
# GitLab CI — integration test checks for connection leaks
pool-health-test:
  stage: test
  script:
    - |
      # Start service + database
      docker compose up -d
      # Run load test
      wrk -t2 -c50 -d30s http://localhost:8080/api/items
      # Check database connection count stayed bounded
      CONNS=$(docker compose exec db psql -U user -d mydb -t -c \
        "SELECT count(*) FROM pg_stat_activity WHERE datname = 'mydb';")
      echo "Active DB connections: $CONNS"
      if [ "$CONNS" -gt 30 ]; then
        echo "ERROR: Connection count exceeded pool max — likely missing pooling"
        exit 1
      fi
  allow_failure: false
```

**Runtime monitoring:**

- Expose pool metrics via Prometheus gauges: `db_pool_active_connections`,
  `db_pool_idle_connections`, `db_pool_wait_duration_seconds`.
- Alert when pool utilisation exceeds 80% sustained or checkout wait time exceeds 1 second.
