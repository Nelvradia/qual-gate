---
title: "Fix: Layer Violation"
status: current
last-updated: 2026-03-19
instrument: architecture-tomographe
severity-range: "Major"
---

# Fix: Layer Violation

## What this means

Your codebase defines architectural layers (e.g., domain, application, infrastructure, API) but
a module is importing from a layer it should not depend on. The classic violation is domain logic
importing infrastructure concerns — a database client, an HTTP library, or a framework-specific
type. Layer violations erode the architecture over time, making the domain untestable without
infrastructure, coupling business logic to specific technologies, and turning what should be a
clean dependency tree into a tangled graph. Even a single violation, once merged, invites more.

## How to fix

### Python

**Define layers with import-linter:**

```toml
# pyproject.toml
[tool.importlinter]
root_package = "mypackage"

[[tool.importlinter.contracts]]
name = "Domain must not import infrastructure"
type = "forbidden"
source_modules = ["mypackage.domain"]
forbidden_modules = [
    "mypackage.infrastructure",
    "mypackage.api",
    "sqlalchemy",
    "requests",
    "fastapi",
]

[[tool.importlinter.contracts]]
name = "Layered architecture"
type = "layers"
layers = [
    "mypackage.api",
    "mypackage.application",
    "mypackage.domain",
]
# Each layer may only import from layers below it
```

```bash
# Check compliance
lint-imports
```

**Fix the violation — move infrastructure out of domain:**

```python
# BEFORE: domain imports a database library directly
# domain/order.py
from sqlalchemy.orm import Session  # layer violation!

class OrderService:
    def __init__(self, db: Session):
        self.db = db
```

```python
# AFTER: domain defines a Protocol; infrastructure implements it

# domain/ports.py
from __future__ import annotations
from typing import Protocol

class OrderRepository(Protocol):
    def save(self, order: Order) -> None: ...

# domain/order.py — no infrastructure imports
from mypackage.domain.ports import OrderRepository

class OrderService:
    def __init__(self, repo: OrderRepository) -> None:
        self.repo = repo

# infrastructure/sql_order_repository.py — allowed to import SQLAlchemy
from sqlalchemy.orm import Session
from mypackage.domain.ports import OrderRepository

class SqlOrderRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def save(self, order: Order) -> None:
        self.session.add(order)
        self.session.commit()
```

### Rust

**Enforce layers via crate boundaries:**

```toml
# Cargo.toml (workspace)
[workspace]
members = [
    "crates/domain",         # zero external deps (only std + serde)
    "crates/application",    # depends on domain
    "crates/infrastructure", # depends on domain (NOT application)
    "crates/api",            # depends on application + domain
]

# crates/domain/Cargo.toml — minimal deps, no infrastructure crates
[dependencies]
serde = { version = "1", features = ["derive"] }
# NO sqlx, reqwest, axum, etc.
```

**Trait-based boundaries within a single crate:**

```rust
// domain/mod.rs — defines traits, never imports infra modules
pub trait OrderRepository: Send + Sync {
    fn save(&self, order: &Order) -> Result<(), DomainError>;
    fn find_by_id(&self, id: &OrderId) -> Result<Option<Order>, DomainError>;
}

// infra/pg_order_repo.rs — implements the trait
use crate::domain::OrderRepository;
use sqlx::PgPool;

pub struct PgOrderRepository {
    pool: PgPool,
}

impl OrderRepository for PgOrderRepository {
    fn save(&self, order: &Order) -> Result<(), DomainError> {
        // SQL implementation
        todo!()
    }
    fn find_by_id(&self, id: &OrderId) -> Result<Option<Order>, DomainError> {
        todo!()
    }
}
```

### TypeScript

**Use ESLint import rules to enforce layers:**

```jsonc
// .eslintrc.json
{
  "rules": {
    "import/no-restricted-paths": ["error", {
      "zones": [
        {
          "target": "./src/domain/**",
          "from": "./src/infrastructure/**",
          "message": "Domain must not import infrastructure."
        },
        {
          "target": "./src/domain/**",
          "from": "./src/api/**",
          "message": "Domain must not import API layer."
        },
        {
          "target": "./src/application/**",
          "from": "./src/api/**",
          "message": "Application must not import API layer."
        }
      ]
    }]
  }
}
```

**Fix the violation:**

```typescript
// BEFORE: domain imports a database driver
// domain/order-service.ts
import { Pool } from "pg";  // layer violation!

// AFTER: domain depends on an interface
// domain/ports/order-repository.ts
export interface OrderRepository {
  save(order: Order): Promise<void>;
  findById(id: string): Promise<Order | null>;
}

// domain/order-service.ts
import { OrderRepository } from "./ports/order-repository";

export class OrderService {
  constructor(private readonly repo: OrderRepository) {}
}

// infrastructure/pg-order-repository.ts — implements the port
import { Pool } from "pg";
import { OrderRepository } from "../domain/ports/order-repository";

export class PgOrderRepository implements OrderRepository {
  constructor(private readonly pool: Pool) {}
  async save(order: Order): Promise<void> { /* ... */ }
  async findById(id: string): Promise<Order | null> { /* ... */ }
}
```

### Go

**Enforce with depguard or go-cleanarch:**

```bash
go install github.com/ryanmoran/depguard@latest

# Or use go-cleanarch for layer checking
go install github.com/roblaszczak/go-cleanarch@latest
go-cleanarch ./...
```

**Package layout enforcing layers:**

```
pkg/
  domain/        # types and interfaces — no infra imports
  application/   # use cases — imports domain only
  infrastructure/ # database, HTTP clients — imports domain
  api/           # HTTP handlers — imports application + domain
```

```go
// pkg/domain/order.go — interface definition
package domain

type OrderRepository interface {
    Save(order *Order) error
    FindByID(id string) (*Order, error)
}

// pkg/infrastructure/pg_order_repo.go — implementation
package infrastructure

import "myapp/pkg/domain"

type PgOrderRepository struct {
    pool *pgxpool.Pool
}

func (r *PgOrderRepository) Save(order *domain.Order) error {
    // ...
}
```

### General

**Recognising layer violations:**

1. Domain code imports a database driver, HTTP client, or framework type.
2. A lower layer references a type defined in a higher layer.
3. Infrastructure concerns (logging configuration, connection strings) appear in domain logic.
4. Test doubles are impossible without standing up real infrastructure.

**Fixing patterns:**

- **Dependency inversion:** Define interfaces at the lower layer boundary. Higher layers
  implement those interfaces. Wire them together at the composition root (main, DI container).
- **Ports and adapters (hexagonal):** Domain defines "ports" (interfaces). Infrastructure
  provides "adapters" (implementations). The application layer orchestrates.
- **Composition root:** All wiring happens in one place (`main.py`, `main.rs`, `main.go`).
  No layer creates its own dependencies — they receive them via constructor injection.

## Prevention

- **CI layer checks (every MR):**
  ```yaml
  layer-check:
    stage: lint
    script:
      - lint-imports                                    # Python
      - npx eslint --rule 'import/no-restricted-paths'  # TypeScript
      - go-cleanarch ./...                              # Go
    allow_failure: false
  ```

- **Fitness functions:** Write tests that assert on the dependency graph. If the domain
  package imports `sqlalchemy`, the test fails.

- **Approved dependency lists per layer:** Document in an ADR which external packages
  each layer may import. Enforce via tooling and review.

- **Code review gate:** Any new import crossing a layer boundary must be flagged.

- **Onboarding docs:** Include a dependency direction diagram in the project architecture
  documentation so new developers know the rules before their first MR.
