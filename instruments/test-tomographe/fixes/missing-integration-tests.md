---
title: "Fix: Missing Integration Tests"
status: current
last-updated: 2026-03-19
instrument: test-tomographe
severity-range: "Major"
---

# Fix: Missing Integration Tests

## What this means

Your project has components that interact with external systems — databases, APIs, message
brokers, file systems, or other services — but lacks tests that verify these interactions with
real dependencies. Unit tests with mocks verify logic in isolation but cannot catch serialisation
bugs, schema mismatches, connection handling errors, or contract violations at component
boundaries. Missing integration tests mean your first real test of these interactions happens in
staging or production, where failures are far more expensive to diagnose.

## How to fix

### Python

**Use testcontainers for real database testing:**

```python
# pip install testcontainers[postgres] pytest

# tests/integration/conftest.py
import pytest
from testcontainers.postgres import PostgresContainer

@pytest.fixture(scope="session")
def postgres_url():
    """Spin up a real PostgreSQL container for the test session."""
    with PostgresContainer("postgres:16-alpine") as pg:
        yield pg.get_connection_url()

@pytest.fixture
def db_session(postgres_url):
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session
    engine = create_engine(postgres_url)
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
        session.rollback()
```

**Test real HTTP client behaviour:**

```python
# tests/integration/test_api_client.py
import responses

@responses.activate
def test_fetch_forecast_parses_response():
    responses.add(
        responses.GET, "https://api.weather.example/v1/forecast",
        json={"temp_c": 22.5, "condition": "clear"}, status=200,
    )
    client = WeatherClient(base_url="https://api.weather.example")
    forecast = client.fetch_forecast(city="berlin")
    assert forecast.temp_c == 22.5, f"Expected 22.5, got {forecast.temp_c}"

@responses.activate
def test_fetch_forecast_handles_server_error():
    responses.add(responses.GET, "https://api.weather.example/v1/forecast", status=503)
    client = WeatherClient(base_url="https://api.weather.example")
    with pytest.raises(ServiceUnavailableError):
        client.fetch_forecast(city="berlin")
```

**Docker-compose test fixtures:**

```yaml
# tests/integration/docker-compose.test.yml
services:
  postgres:
    image: postgres:16-alpine
    environment: { POSTGRES_DB: testdb, POSTGRES_USER: test, POSTGRES_PASSWORD: test }
    ports: ["5433:5432"]
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U test -d testdb"]
      interval: 2s
      timeout: 5s
      retries: 5
```

### Rust

**Use testcontainers-rs for database testing:**

```rust
// tests/integration/test_db.rs
use testcontainers::runners::AsyncRunner;
use testcontainers_modules::postgres::Postgres;
use sqlx::PgPool;

#[tokio::test]
async fn user_repository_stores_and_retrieves() {
    let container = Postgres::default().start().await.unwrap();
    let port = container.get_host_port_ipv4(5432).await.unwrap();
    let url = format!("postgres://postgres:postgres@127.0.0.1:{port}/postgres");
    let pool = PgPool::connect(&url).await.unwrap();
    sqlx::migrate!("./migrations").run(&pool).await.unwrap();

    let repo = UserRepository::new(pool.clone());
    let user_id = repo.create("alice", "alice@example.com").await.unwrap();
    assert!(user_id > 0, "Expected positive user ID, got {user_id}");

    let user = repo.find_by_id(user_id).await.unwrap();
    assert_eq!(user.name, "alice");
    assert_eq!(user.email, "alice@example.com");
}
```

### TypeScript

**Use supertest for HTTP API integration tests:**

```typescript
// tests/integration/api.test.ts
import request from "supertest";
import { createApp } from "../../src/app";

describe("POST /api/users", () => {
  let app: Express.Application;

  beforeAll(async () => {
    await setupTestDatabase();
    app = createApp({ databaseUrl: process.env.TEST_DATABASE_URL });
  });

  afterAll(() => teardownTestDatabase());

  it("creates a user and returns 201", async () => {
    const response = await request(app)
      .post("/api/users")
      .send({ name: "Alice", email: "alice@example.com" })
      .expect(201);
    expect(response.body).toMatchObject({ name: "Alice", email: "alice@example.com" });
    expect(response.body.id).toBeDefined();
  });

  it("returns 409 for duplicate email", async () => {
    await request(app).post("/api/users").send({ name: "A", email: "dup@ex.com" }).expect(201);
    await request(app).post("/api/users").send({ name: "B", email: "dup@ex.com" }).expect(409);
  });
});
```

**Use testcontainers-node for services:**

```typescript
import { PostgreSqlContainer } from "@testcontainers/postgresql";

let container: StartedPostgreSqlContainer;
beforeAll(async () => {
  container = await new PostgreSqlContainer("postgres:16-alpine").start();
  process.env.TEST_DATABASE_URL = container.getConnectionUri();
}, 60_000);
afterAll(() => container.stop());
```

### Go

**Use testcontainers-go for real service testing:**

```go
// tests/integration/db_test.go
func setupPostgres(t *testing.T) string {
    t.Helper()
    ctx := context.Background()
    container, err := postgres.Run(ctx, "postgres:16-alpine",
        postgres.WithDatabase("testdb"),
        postgres.WithUsername("test"),
        postgres.WithPassword("test"),
        testcontainers.WithWaitStrategy(
            wait.ForLog("database system is ready").WithOccurrence(2),
        ),
    )
    if err != nil {
        t.Fatalf("failed to start postgres: %v", err)
    }
    t.Cleanup(func() { container.Terminate(ctx) })
    connStr, _ := container.ConnectionString(ctx, "sslmode=disable")
    return connStr
}

func TestUserRepository_CreateAndFind(t *testing.T) {
    connStr := setupPostgres(t)
    repo := NewUserRepository(connStr)
    id, err := repo.Create(context.Background(), "alice", "alice@example.com")
    if err != nil {
        t.Fatalf("Create failed: %v", err)
    }
    if id <= 0 {
        t.Errorf("expected positive ID, got %d", id)
    }
}
```

### General

**Identifying integration test gaps:**

1. **Map your boundaries.** List every external system your code communicates with: databases,
   HTTP APIs, message queues, file systems, caches. Each needs at least one integration test.
2. **Check the mock-to-real ratio.** If a component has 20 unit tests mocking a database but
   zero tests against a real database, only the mocks are being tested.
3. **Trace failure scenarios.** For each boundary: what happens when the dependency is slow,
   returns unexpected data, or is unavailable? Each scenario needs a test.
4. **Test data round-trips.** Write a value, read it back, assert equality. This catches
   serialisation bugs, encoding issues, and schema drift.

**What integration tests should NOT do:**

- Test internal logic (that is what unit tests are for).
- Require manual setup steps beyond `docker compose up`.
- Take more than 30 seconds each. Parallelise where possible.
- Leave side effects (temp files, database rows, running containers) after completion.

## Prevention

**CI pipeline with test containers:**

```yaml
# GitLab CI example
integration-tests:
  stage: test
  image: python:3.12-slim
  services:
    - postgres:16-alpine
    - redis:7-alpine
  variables:
    DATABASE_URL: "postgresql://testuser:testpass@postgres:5432/testdb"
  script:
    - pytest tests/integration/ -v --timeout=30
  allow_failure: false
```

**Code review checklist:**

- Does the MR add a new external dependency or API call? Where is the integration test?
- Do new integration tests clean up after themselves?

**Boundary inventory:** Maintain a list of external boundaries in your project docs. Each entry
should link to its corresponding integration test file. Review quarterly for gaps.
