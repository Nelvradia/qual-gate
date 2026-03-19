---
title: "Fix: Schema–Documentation Drift"
status: current
last-updated: 2026-03-19
instrument: data-tomographe
severity-range: "Minor–Major"
---

# Fix: Schema–Documentation Drift

## What this means

Your database schema and its documentation are out of sync. This happens when schema changes
(new columns, altered types, dropped tables) are applied through migrations but the corresponding
documentation — ERD diagrams, data dictionaries, API docs referencing database fields — is not
updated. The drift creates confusion for developers who rely on docs to understand data
relationships, leads to incorrect integration assumptions, and can cause bugs when new team
members write queries based on stale documentation. Minor drift (a few undocumented columns) is
low-risk, but major drift (entire tables or relationships missing from docs) can cause costly
misunderstandings in cross-team systems.

## How to fix

### Python

**Auto-generate schema docs from SQLAlchemy models:**

```python
# scripts/generate_schema_docs.py
"""Generate Markdown data dictionary from SQLAlchemy models."""
from __future__ import annotations

import importlib
import inspect

from sqlalchemy import inspect as sa_inspect
from sqlalchemy.orm import DeclarativeBase


def generate_data_dictionary(base_class: type[DeclarativeBase]) -> str:
    """Produce a Markdown table for every mapped table."""
    lines = ["# Data Dictionary\n", f"Generated from `{base_class.__module__}`.\n"]

    for mapper in base_class.registry.mappers:
        cls = mapper.class_
        table = mapper.local_table
        lines.append(f"## {table.name}\n")
        lines.append(f"Model: `{cls.__name__}` | Schema: `{table.schema or 'public'}`\n")
        lines.append("| Column | Type | Nullable | Default | Description |")
        lines.append("|--------|------|----------|---------|-------------|")

        for col in table.columns:
            doc = col.comment or col.doc or "—"
            default = str(col.server_default.arg) if col.server_default else "—"
            lines.append(
                f"| {col.name} | {col.type} | {col.nullable} | {default} | {doc} |"
            )
        lines.append("")

    return "\n".join(lines)
```

**Diff schema against docs with Alembic:**

```bash
# Compare current DB state to model definitions
alembic check

# Auto-generate a migration if models changed
alembic revision --autogenerate -m "sync schema with models"

# After migration, regenerate docs
python scripts/generate_schema_docs.py > docs/data-dictionary.md
```

**Use `sqlalchemy.Column.doc` and `comment` consistently:**

```python
from sqlalchemy.orm import Mapped, mapped_column

class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        doc="Internal order identifier",
        comment="Internal order identifier",  # persisted in DB metadata
    )
    status: Mapped[str] = mapped_column(
        doc="One of: pending, confirmed, shipped, delivered, cancelled",
        comment="One of: pending, confirmed, shipped, delivered, cancelled",
    )
```

### Rust

**Generate schema docs from Diesel models:**

```rust
// build.rs — extract table! macro definitions into Markdown at build time
// For runtime introspection, query information_schema directly.

use std::fs;
use std::process::Command;

fn main() {
    // Dump schema from the database and write a Markdown summary
    let output = Command::new("diesel")
        .args(["print-schema"])
        .output()
        .expect("diesel CLI must be installed");

    let schema = String::from_utf8_lossy(&output.stdout);
    let doc = format!("# Auto-Generated Schema Reference\n\n```rust\n{schema}\n```\n");
    fs::write("docs/schema-reference.md", doc).expect("write schema docs");
}
```

**With `sqlx`, use compile-time checked queries and extract metadata:**

```bash
# Record query metadata for offline checking
cargo sqlx prepare --workspace

# Verify schema matches compiled queries
cargo sqlx prepare --check --workspace

# Generate schema dump for documentation
psql "$DATABASE_URL" -c "\d+" > docs/schema-dump.txt
```

### TypeScript

**Auto-generate docs from Prisma schema:**

```bash
# Install the ERD generator
npm install -D prisma-erd-generator @mermaid-js/mermaid-cli

# Add to schema.prisma
# generator erd {
#   provider = "prisma-erd-generator"
#   output   = "../docs/erd.svg"
# }

# Generate docs alongside client
npx prisma generate

# Validate schema consistency
npx prisma validate
```

**Generate a data dictionary from Prisma DMMF:**

```typescript
// scripts/generate-data-dict.ts
import { getDMMF } from "@prisma/internals";
import { readFileSync, writeFileSync } from "fs";

async function generateDocs(): Promise<void> {
  const schema = readFileSync("prisma/schema.prisma", "utf-8");
  const dmmf = await getDMMF({ datamodel: schema });

  const lines: string[] = ["# Data Dictionary\n"];

  for (const model of dmmf.datamodel.models) {
    lines.push(`## ${model.name}\n`);
    lines.push("| Field | Type | Required | Default | Documentation |");
    lines.push("|-------|------|----------|---------|---------------|");
    for (const field of model.fields) {
      const doc = field.documentation ?? "—";
      const def = field.default
        ? JSON.stringify(field.default)
        : "—";
      lines.push(
        `| ${field.name} | ${field.type} | ${field.isRequired} | ${def} | ${doc} |`,
      );
    }
    lines.push("");
  }

  writeFileSync("docs/data-dictionary.md", lines.join("\n"));
}

generateDocs();
```

### Go

**Generate docs from `golang-migrate` migration files:**

```bash
# List applied migrations
migrate -database "$DATABASE_URL" -path db/migrations version

# Dump current schema for documentation
pg_dump --schema-only "$DATABASE_URL" > docs/schema.sql
```

**Use `sqlc` to keep queries and schema in sync:**

```yaml
# sqlc.yaml
version: "2"
sql:
  - engine: "postgresql"
    queries: "db/queries/"
    schema: "db/migrations/"
    gen:
      go:
        package: "db"
        out: "internal/db"
```

```bash
# Regenerate Go code from schema + queries — fails if they drift
sqlc generate

# Verify without generating
sqlc vet
```

### General

**Schema diff tools (database-agnostic):**

- **SchemaSpy:** Generates HTML documentation with ERD diagrams directly from a live database.
  Run it after each migration to produce up-to-date docs.
- **Atlas:** Declarative schema management with built-in `atlas schema diff` to compare two
  schema states and produce a human-readable diff.
- **pg_dump --schema-only / mysqldump --no-data:** Snapshot the schema after each migration,
  commit the snapshot, and diff it in code review.

**Embedding documentation in the schema itself:**

Use `COMMENT ON` statements in migrations so the database is self-documenting:

```sql
COMMENT ON TABLE orders IS 'Customer purchase orders';
COMMENT ON COLUMN orders.status IS 'Lifecycle state: pending → confirmed → shipped → delivered';
```

Then extract comments with tools like SchemaSpy or a simple query:

```sql
SELECT c.table_name, c.column_name, pgd.description
FROM information_schema.columns c
JOIN pg_catalog.pg_description pgd
  ON pgd.objsubid = c.ordinal_position
 AND pgd.objoid = (c.table_schema || '.' || c.table_name)::regclass
WHERE c.table_schema = 'public';
```

## Prevention

**CI pipeline gate — detect schema/doc drift:**

```yaml
# GitLab CI
schema-doc-check:
  stage: lint
  script:
    - python scripts/generate_schema_docs.py > /tmp/generated-dict.md
    - diff docs/data-dictionary.md /tmp/generated-dict.md
      || (echo "Schema docs are stale. Regenerate with: make docs-schema" && exit 1)
  rules:
    - changes:
        - "db/migrations/**"
        - "src/models/**"
```

**Pre-commit hook to regenerate docs when models change:**

```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: schema-docs
        name: regenerate schema docs
        entry: python scripts/generate_schema_docs.py > docs/data-dictionary.md
        language: system
        files: '(models/|migrations/)'
        pass_filenames: false
```

**Process guardrails:**

- Require that any MR touching migrations also updates `docs/data-dictionary.md` or runs the
  auto-generation script. Enforce via MR template checklist.
- Pin a schema snapshot file (e.g., `docs/schema.sql`) in version control. CI diffs it against
  the live schema after running migrations on a test database.
- Schedule weekly schema doc generation in CI and open an MR if drift is detected.
