---
title: "Fix: Migration Integrity"
status: current
last-updated: 2026-03-19
instrument: data-tomographe
severity-range: "Major–Critical"
---

# Fix: Migration Integrity

## What this means

Database migrations in your project have integrity issues: they may fail on a clean database,
produce different results when re-run, lack rollback support, or conflict with migrations from
other branches. Broken migrations are Critical because they can corrupt production data, block
deployments, or leave the database in an inconsistent state that requires manual intervention.
At minimum, every migration must be tested forward (upgrade) and backward (downgrade), run
idempotently where possible, and pass through a CI gate before reaching any shared environment.

## How to fix

### Python

**Alembic — test migrations in CI:**

```python
# tests/integration/test_migrations.py
"""Verify all migrations apply cleanly and roll back without errors."""
from __future__ import annotations

import pytest
from alembic import command
from alembic.config import Config


@pytest.fixture
def alembic_cfg(tmp_path, test_database_url: str) -> Config:
    """Alembic config pointing at a disposable test database."""
    cfg = Config("alembic.ini")
    cfg.set_main_option("sqlalchemy.url", test_database_url)
    return cfg


def test_upgrade_to_head(alembic_cfg: Config) -> None:
    """All migrations apply from an empty database to head."""
    command.upgrade(alembic_cfg, "head")


def test_full_downgrade(alembic_cfg: Config) -> None:
    """Upgrade to head, then downgrade back to base without errors."""
    command.upgrade(alembic_cfg, "head")
    command.downgrade(alembic_cfg, "base")


def test_upgrade_downgrade_each_step(alembic_cfg: Config) -> None:
    """Walk through every revision forward and backward one step at a time."""
    from alembic.script import ScriptDirectory

    script = ScriptDirectory.from_config(alembic_cfg)
    revisions = list(script.walk_revisions())
    revisions.reverse()  # oldest first

    for rev in revisions:
        command.upgrade(alembic_cfg, rev.revision)

    for rev in reversed(revisions):
        command.downgrade(alembic_cfg, rev.down_revision or "base")
```

**Detect branch conflicts:**

```bash
# Fail if two migration heads exist (parallel branches created conflicting migrations)
HEADS=$(alembic heads | wc -l)
if [ "$HEADS" -gt 1 ]; then
    echo "ERROR: Multiple migration heads. Merge: alembic merge heads -m 'merge'"
    exit 1
fi
```

### Rust

**Diesel — migration testing:**

```rust
// tests/integration/migrations.rs
use diesel::prelude::*;
use diesel::pg::PgConnection;

#[test]
fn test_migrations_run_cleanly() {
    let url = std::env::var("TEST_DATABASE_URL")
        .expect("TEST_DATABASE_URL must be set");
    let mut conn = PgConnection::establish(&url)
        .expect("connect to test database");

    // Run all pending migrations
    diesel_migrations::run_pending_migrations(&mut conn)
        .expect("all migrations should apply cleanly");
}

#[test]
fn test_migrations_are_reversible() {
    let url = std::env::var("TEST_DATABASE_URL")
        .expect("TEST_DATABASE_URL must be set");
    let mut conn = PgConnection::establish(&url)
        .expect("connect to test database");

    // Apply all, then revert all
    diesel_migrations::run_pending_migrations(&mut conn).unwrap();
    diesel_migrations::revert_all_migrations(&mut conn)
        .expect("all migrations should revert cleanly");
}
```

**sqlx — compile-time verification:**

```bash
cargo sqlx prepare --check --workspace  # verify migrations match compiled queries
sqlx migrate run --database-url "$TEST_DATABASE_URL"
sqlx migrate revert --database-url "$TEST_DATABASE_URL"  # test rollback
```

Every Diesel migration directory must have both `up.sql` and `down.sql` — never leave
`down.sql` empty.

### TypeScript

**Prisma — migration testing:**

```bash
# Create migration without applying (for review)
npx prisma migrate dev --create-only --name add_order_status

# Apply migrations to a test database
DATABASE_URL="$TEST_DATABASE_URL" npx prisma migrate deploy

# Reset and re-apply all migrations (tests full upgrade path)
DATABASE_URL="$TEST_DATABASE_URL" npx prisma migrate reset --force

# Verify schema is in sync with migrations
npx prisma migrate diff \
  --from-schema-datamodel prisma/schema.prisma \
  --to-migrations-directory prisma/migrations \
  --exit-code
```

**Knex — migration testing:**

```typescript
// tests/integration/migrations.test.ts
import knex from "knex";
import config from "../../knexfile";

describe("migrations", () => {
  const db = knex(config.test);
  afterAll(() => db.destroy());

  it("applies all migrations from scratch", async () => {
    await db.migrate.rollback(undefined, true);
    await db.migrate.latest();
    const [, pending] = await db.migrate.list();
    expect(pending).toHaveLength(0);
  });

  it("rolls back all migrations without errors", async () => {
    await db.migrate.latest();
    await db.migrate.rollback(undefined, true);
  });
});
```

### Go

**golang-migrate — migration testing:**

```go
// migrations_test.go
package migrations_test

import (
    "database/sql"
    "testing"

    "github.com/golang-migrate/migrate/v4"
    "github.com/golang-migrate/migrate/v4/database/postgres"
    _ "github.com/golang-migrate/migrate/v4/source/file"
    _ "github.com/lib/pq"
)

func TestMigrationsUpDown(t *testing.T) {
    db, err := sql.Open("postgres", testDatabaseURL(t))
    if err != nil {
        t.Fatalf("connect: %v", err)
    }
    defer db.Close()

    driver, err := postgres.WithInstance(db, &postgres.Config{})
    if err != nil {
        t.Fatalf("driver: %v", err)
    }

    m, err := migrate.NewWithDatabaseInstance("file://db/migrations", "postgres", driver)
    if err != nil {
        t.Fatalf("init migrate: %v", err)
    }

    if err := m.Up(); err != nil && err != migrate.ErrNoChange {
        t.Fatalf("migrate up: %v", err)
    }
    if err := m.Down(); err != nil && err != migrate.ErrNoChange {
        t.Fatalf("migrate down: %v", err)
    }
}
```

Every `*.up.sql` must have a matching `*.down.sql`. Validate pairing in CI:

```bash
for up in db/migrations/*.up.sql; do
    down="${up/.up.sql/.down.sql}"
    [ -f "$down" ] || { echo "ERROR: Missing $down"; exit 1; }
done
```

### General

**Idempotency — write migrations defensively:**

```sql
-- GOOD: idempotent — safe to re-run
CREATE TABLE IF NOT EXISTS audit_log (...);
CREATE INDEX IF NOT EXISTS idx_audit_log_ts ON audit_log (created_at);

-- GOOD: guard column additions
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'users' AND column_name = 'email_verified'
    ) THEN
        ALTER TABLE users ADD COLUMN email_verified BOOLEAN DEFAULT FALSE;
    END IF;
END $$;

-- BAD: will fail if run twice
CREATE TABLE audit_log (...);
ALTER TABLE users ADD COLUMN email_verified BOOLEAN;
```

**Rollback verification checklist:**

1. Does `down.sql` / `downgrade()` undo every change in `up.sql` / `upgrade()`?
2. After rolling back, does the application at the previous version still work?
3. Are there data-loss risks? (Dropping a column loses its data permanently.)
4. Is the rollback tested in CI, not just the upgrade?

## Prevention

**CI pipeline — migration integrity gate:**

```yaml
# GitLab CI
migration-test:
  stage: test
  services:
    - postgres:16-alpine
  variables:
    POSTGRES_DB: test_migrations
    POSTGRES_USER: test
    POSTGRES_PASSWORD: test
    TEST_DATABASE_URL: "postgresql://test:test@postgres:5432/test_migrations"
  script:
    # Detect multiple migration heads (branch conflicts)
    - alembic heads | wc -l | xargs -I{} test {} -eq 1
    # Upgrade from empty to head
    - alembic upgrade head
    # Downgrade back to base
    - alembic downgrade base
    # Upgrade again to verify idempotency
    - alembic upgrade head
  rules:
    - changes:
        - "db/migrations/**"
        - "alembic/**"
        - "src/models/**"
```

**Branch conflict detection:** Check migration history is linear in CI. Alembic:
`alembic heads` must return exactly one revision. Require DB-owner review for migrations.

**Production guardrails:** Run migrations in a transaction (PostgreSQL supports transactional
DDL). Snapshot the database before migrating. Set a migration timeout. Never apply migrations
and deploy new code simultaneously — migrate first, verify, then deploy.
