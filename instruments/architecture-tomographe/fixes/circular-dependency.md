---
title: "Fix: Circular Dependency"
status: current
last-updated: 2026-03-19
instrument: architecture-tomographe
severity-range: "Major–Critical"
---

# Fix: Circular Dependency

## What this means

Two or more modules depend on each other, directly or transitively, forming a cycle in the
dependency graph. Circular dependencies make the codebase resistant to change — modifying any
module in the cycle risks breaking all the others. They prevent independent compilation, testing,
and deployment. In compiled languages they can cause build failures outright; in interpreted
languages they cause subtle import-time errors or force import-order hacks. At the architecture
level, cycles indicate that module boundaries are poorly defined and responsibilities are tangled.

## How to fix

### Python

**Detect cycles with pydeps or import-linter:**

```bash
# Install detection tools
pip install pydeps import-linter

# Visualise the dependency graph (highlights cycles in red)
pydeps src/mypackage --cluster --max-bacon=4

# Define and check layered contracts
# setup.cfg or pyproject.toml
```

```toml
# pyproject.toml — import-linter configuration
[tool.importlinter]
root_package = "mypackage"

[[tool.importlinter.contracts]]
name = "No circular imports"
type = "independence"
modules = [
    "mypackage.domain",
    "mypackage.infrastructure",
    "mypackage.api",
]
```

**Break cycles with dependency inversion:**

```python
# BEFORE: circular — service.py imports repository.py, repository.py imports service.py

# service.py
from mypackage.repository import UserRepository  # direct dependency

class UserService:
    def __init__(self):
        self.repo = UserRepository()

# repository.py
from mypackage.service import UserService  # circular!
```

```python
# AFTER: introduce an interface (protocol) in a shared module

# ports.py — no imports from service or repository
from __future__ import annotations

from typing import Protocol

class UserRepositoryPort(Protocol):
    def find_by_id(self, user_id: str) -> dict: ...
    def save(self, user: dict) -> None: ...

# service.py — depends only on the port
from mypackage.ports import UserRepositoryPort

class UserService:
    def __init__(self, repo: UserRepositoryPort) -> None:
        self.repo = repo

# repository.py — implements the port, no import of service
from mypackage.ports import UserRepositoryPort

class SqlUserRepository:
    """Implements UserRepositoryPort against a SQL database."""
    def find_by_id(self, user_id: str) -> dict:
        ...
    def save(self, user: dict) -> None:
        ...
```

### Rust

**Detect cycles with cargo-depgraph:**

```bash
cargo install cargo-depgraph

# Generate dependency graph (inter-crate cycles are compile errors,
# but intra-crate module cycles can still exist)
cargo depgraph --all-deps | dot -Tpng -o deps.png
```

**Break intra-crate module cycles with traits:**

```rust
// BEFORE: mod a uses mod b, mod b uses mod a

// AFTER: define a trait in a shared location

// traits.rs — no dependencies on a or b
pub trait Repository {
    fn find(&self, id: &str) -> Option<Entity>;
    fn save(&self, entity: &Entity) -> Result<(), Error>;
}

// service.rs — depends on traits, not on repository directly
use crate::traits::Repository;

pub struct UserService<R: Repository> {
    repo: R,
}

impl<R: Repository> UserService<R> {
    pub fn new(repo: R) -> Self {
        Self { repo }
    }
}

// repository.rs — implements the trait, no dependency on service
use crate::traits::Repository;

pub struct SqlRepository { /* ... */ }

impl Repository for SqlRepository {
    fn find(&self, id: &str) -> Option<Entity> { todo!() }
    fn save(&self, entity: &Entity) -> Result<(), Error> { todo!() }
}
```

**Split into separate crates for inter-crate enforcement:**

```toml
# Cargo.toml (workspace)
[workspace]
members = [
    "crates/domain",       # core types and traits — no internal deps
    "crates/application",  # depends on domain only
    "crates/infrastructure", # depends on domain only
    "crates/api",          # depends on application and domain
]
```

### TypeScript

**Detect cycles with madge:**

```bash
npx madge --circular --extensions ts src/

# Visual graph output
npx madge --image graph.png --extensions ts src/
```

**Break cycles with interface extraction:**

```typescript
// interfaces/user-repository.ts — shared contract, no circular imports
export interface UserRepository {
  findById(id: string): Promise<User | null>;
  save(user: User): Promise<void>;
}

// services/user-service.ts — depends on interface only
import { UserRepository } from "../interfaces/user-repository";

export class UserService {
  constructor(private readonly repo: UserRepository) {}
}

// repositories/sql-user-repository.ts — implements interface
import { UserRepository } from "../interfaces/user-repository";

export class SqlUserRepository implements UserRepository {
  async findById(id: string): Promise<User | null> { /* ... */ }
  async save(user: User): Promise<void> { /* ... */ }
}
```

**Use barrel files carefully — they are a common source of accidental cycles:**

```typescript
// BAD: index.ts re-exports everything, creating hidden cycles
// export * from "./service";
// export * from "./repository";

// GOOD: import directly from the specific module
import { UserService } from "./services/user-service";
```

### Go

**Detect cycles (the compiler already rejects package-level cycles):**

```bash
# Go refuses to compile circular package imports.
# For visualisation and architecture review:
go install github.com/kisielk/godepgraph@latest
godepgraph -s ./... | dot -Tpng -o deps.png
```

**Break cycles with interface packages:**

```go
// pkg/ports/repository.go — interface package, no implementation imports
package ports

type UserRepository interface {
    FindByID(id string) (*User, error)
    Save(user *User) error
}

// pkg/service/user.go — depends on ports, not on the repository package
package service

import "myapp/pkg/ports"

type UserService struct {
    repo ports.UserRepository
}

// pkg/repository/sql.go — implements the interface
package repository

import "myapp/pkg/ports"

type SQLUserRepository struct{ /* ... */ }

func (r *SQLUserRepository) FindByID(id string) (*ports.User, error) {
    // ...
}
```

### General

**Strategies for breaking circular dependencies (language-agnostic):**

1. **Dependency inversion.** Introduce an interface (protocol, trait, abstract class) in a
   module that sits below both participants in the cycle. Both modules depend on the
   interface; neither depends on the other.

2. **Extract shared types.** If modules are circular because they share data structures, move
   those structures into a dedicated "models" or "types" module with no internal dependencies.

3. **Merge if truly inseparable.** If two modules are so tightly coupled that separating them
   requires tortured abstractions, they may belong together. Merge them into one module with
   a clear single responsibility.

4. **Event-driven decoupling.** Replace direct calls with an event bus or message queue.
   Module A publishes an event; module B subscribes. Neither imports the other.

5. **Dependency graph visualisation.** Generate a graph regularly and review it. Cycles are
   immediately visible as loops. Tools: `pydeps`, `madge`, `cargo-depgraph`, `godepgraph`.

## Prevention

- **CI enforcement:** Run cycle detection on every MR and fail the pipeline if new cycles
  appear:
  ```yaml
  # GitLab CI
  check-cycles:
    stage: lint
    script:
      - import-linter --config pyproject.toml     # Python
      - npx madge --circular --extensions ts src/  # TypeScript
      - cargo deny check                           # Rust (inter-crate)
    allow_failure: false
  ```

- **Module dependency policy:** Define allowed dependency directions in a config file
  (import-linter contracts, ArchUnit rules) and enforce in CI. Document in an ADR.

- **Code review checklist:** Reviewers must check that new imports do not introduce cycles.

- **Multi-package structure:** For larger projects, split into separate packages or crates.
  The compiler enforces acyclicity at the package boundary.
