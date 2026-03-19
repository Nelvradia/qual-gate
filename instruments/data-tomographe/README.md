# data-tomographe

**Data and schema health scanner for the target project.** Audits schema alignment with documentation, migration integrity, cross-database consistency, backup coverage, data classification tier enforcement, and data lifecycle. Replaces manual schema inspection approaches.

**Covers DR Sections:** S8 (Data Management)

---

## Quick Start

```bash
"Read instruments/data-tomographe/README.md and execute a full data scan."
"Read instruments/data-tomographe/README.md and execute Phase 3 (Data Classification Tiers) only."
```

---

## Scan Phases

| Phase | Name | What It Does | Requires Running DB? |
|-------|------|-------------|---------------------|
| **1** | Schema Alignment | Compare schema documentation to actual migration code | No |
| **2** | Migration Health | Verify migration ordering, idempotency, rollback | No |
| **3** | Data Classification Tiers | Verify tier assignments and encryption per classification level | No |
| **4** | Cross-DB Integrity | Verify referential integrity across databases | No |
| **5** | Backup Coverage | Audit which data stores are backed up and how | No (reads config) |
| **6** | Data Lifecycle | Check retention policies, cleanup mechanisms, growth estimates | No |
| **7** | Report | Compile findings | No |

---

## Phase 1 — Schema Alignment

**Goal:** Verify schema documentation matches actual migration code.

```bash
# Tables documented in schema docs
grep -oP '\b[a-z_]+\b' docs/schema-map.md 2>/dev/null | \
  grep -E '^[a-z]{3,}' | sort -u > /tmp/doc_tables.txt
# More precise: look for CREATE TABLE references
grep -oP 'CREATE TABLE (\w+)' docs/schema-map.md 2>/dev/null | \
  awk '{print $3}' | sort -u >> /tmp/doc_tables.txt
sort -u /tmp/doc_tables.txt -o /tmp/doc_tables.txt

# Tables in migration code
grep -rn 'CREATE TABLE' src/db/ --include='*.rs' | \
  sed 's/.*CREATE TABLE \(IF NOT EXISTS \)\?\([a-z_]*\).*/\2/' | sort -u > /tmp/code_tables.txt
echo "Documented tables: $(wc -l < /tmp/doc_tables.txt)"
echo "Code tables: $(wc -l < /tmp/code_tables.txt)"

# Tables in code but not in docs (documentation is stale)
comm -13 /tmp/doc_tables.txt /tmp/code_tables.txt > /tmp/undocumented.txt
echo "=== Undocumented tables ==="
cat /tmp/undocumented.txt

# Tables in docs but not in code (docs reference removed/renamed tables)
comm -23 /tmp/doc_tables.txt /tmp/code_tables.txt > /tmp/stale_doc.txt
echo "=== Stale doc references ==="
cat /tmp/stale_doc.txt

# Column-level check (for high-value tables)
# Extract column definitions from code and compare against schema docs
for table in conversations messages corrections templates; do
  echo "=== $table columns ==="
  grep -A30 "CREATE TABLE.*$table" src/db/ --include='*.rs' -r | \
    grep -oP '^\s+(\w+)\s+(TEXT|INTEGER|REAL|BLOB)' | head -20
done
```

### Severity Rules

| Finding | Severity |
|---------|----------|
| Table in code but not in schema docs | **Minor** (doc stale) |
| Table in schema docs but not in code | **Minor** (doc references removed table) |
| >5 undocumented tables | **Major** (schema docs significantly out of sync) |
| Core table columns don't match schema docs | **Minor** |

---

## Phase 2 — Migration Health

**Goal:** Verify migration system is robust and correct.

```bash
# Migration files inventory
find src/db/ -name '*.rs' | xargs grep -l 'CREATE TABLE\|ALTER TABLE' 2>/dev/null

# Migration versioning scheme
grep -rn 'migration\|version\|schema_version\|PRAGMA user_version' src/db/ --include='*.rs' | head -20

# Per-service migration count
for svc in $(ls src/db/ 2>/dev/null); do
  count=$(grep -rn "CREATE TABLE\|ALTER TABLE" src/db/${svc}*.rs 2>/dev/null | wc -l)
  echo "$svc: $count migration statements"
done

# Forward-compatibility columns (added early, used later)
grep -rn 'forward_compat\|_reserved\|-- Phase' src/db/ --include='*.rs' | head -10

# Rollback capability
grep -rn 'DROP TABLE\|ALTER TABLE.*DROP\|down_migration\|rollback' src/db/ --include='*.rs' | head -10

# Idempotency (IF NOT EXISTS / IF EXISTS)
NO_IDEMPOTENT=$(grep -rn 'CREATE TABLE' src/db/ --include='*.rs' | grep -v 'IF NOT EXISTS' | wc -l)
echo "Non-idempotent CREATE TABLE: $NO_IDEMPOTENT"

# Migration tests
find tests/ -name '*migration*' -o -name '*schema*' 2>/dev/null
grep -rn 'migration\|schema' tests/ --include='*.rs' --include='*.py' 2>/dev/null | wc -l
```

### Checklist

- [ ] All CREATE TABLE use IF NOT EXISTS (idempotent)
- [ ] All ALTER TABLE have corresponding tests
- [ ] Schema version tracked (PRAGMA user_version or equivalent)
- [ ] Migration runs are tested in CI (fresh DB + migration path)
- [ ] Forward-compatibility columns documented
- [ ] Down migrations exist for reversibility (or documented as irreversible)

---

## Phase 3 — Data Classification Tiers

**Goal:** Verify data classification and encryption by tier level.

```bash
# Data classification tiers (from project's data classification policy):
# Public     — system config, no encryption needed
# Internal   — operational data, standard storage
# Confidential — personal data, encrypted storage
# Restricted — health/financial data, encrypted storage + audit trail

# Which databases exist and their classification tier
grep -rn 'privacy\|tier\|classification\|data_class' src/db/ config/ --include='*.rs' --include='*.yaml' | head -20

# Encrypted storage usage per database
grep -rn 'sqlcipher\|cipher\|PRAGMA key\|PRAGMA cipher\|encrypt' src/db/ --include='*.rs' | head -10

# Databases that should be encrypted (Confidential/Restricted)
echo "Expected encrypted: databases storing personal, health, or financial data"
echo "Expected plaintext: databases storing only Public/Internal data"

# Data access patterns
# Confidential/Restricted data should only be accessed through specific code paths
grep -rn 'health\|financial\|medical\|personal' src/ --include='*.rs' | head -10

# Audit trail for Restricted data access
grep -rn 'audit\|access_log\|data_access' src/ --include='*.rs' | head -10
```

### Data Classification Tier Matrix

| Database | Expected Tier | Encryption | Audit | Check |
|---|---|---|---|---|
| main.db | Internal | Plain SQLite | No | Verify no Confidential/Restricted data stored here |
| config.db | Public | Plain SQLite | No | Config only, no personal data |
| (internal data) | Internal | Plain SQLite | No | Task data, no PII |
| notifications.db | Internal | Plain SQLite | No | Notification metadata |
| (sensitive data) | Confidential/Restricted | Encrypted storage | Yes | Verify encryption active |

---

## Phase 4 — Cross-DB Integrity

**Goal:** Verify data consistency across databases.

```bash
# Shared identifiers across databases
# Common IDs should be consistent across all stores
for id in conversation_id user_id component_id thread_id; do
  echo "=== $id usage ==="
  grep -rn "$id" src/db/ --include='*.rs' | head -10
done

# Foreign key enforcement
grep -rn 'PRAGMA foreign_keys' src/db/ --include='*.rs' | head -5
# Should be ON for all databases

# Cross-database references (data in DB A references data in DB B)
# These can't use SQL foreign keys — must be application-level checks
grep -rn 'REFERENCES\|JOIN\|SELECT.*FROM.*WHERE.*IN' src/db/ --include='*.rs' | head -20

# Orphan detection patterns
# Do any cleanup/gc mechanisms exist?
grep -rn 'cleanup\|garbage\|orphan\|prune\|expire' src/db/ --include='*.rs' | head -10
```

---

## Phase 5 — Backup Coverage

**Goal:** Verify all important data stores are backed up.

```bash
# Backup configuration
grep -rn 'backup' config/ docker-compose.yml docs/operations/ --include='*.yaml' --include='*.yml' --include='*.md' 2>/dev/null | head -20

# Backup script
find infra/scripts/ -name '*backup*' 2>/dev/null

# Which data stores are backed up?
echo "=== Data stores to back up ==="
echo "1. Databases (all SQLite / PostgreSQL / etc.)"
echo "2. Vector database data (if applicable)"
echo "3. Personality/configuration files"
echo "4. Encryption keys (device keys, E2E keys)"
echo "5. Application configuration files"

# Backup schedule
grep -rn 'cron\|schedule\|periodic\|interval.*backup' config/ infra/ --include='*.yaml' --include='*.yml' 2>/dev/null

# Disaster recovery runbook
cat docs/operations/disaster-recovery-runbook.md 2>/dev/null | head -20
```

### Backup Checklist

- [ ] All databases included in backup
- [ ] Vector store data backed up (or rebuildable from source)
- [ ] Personality/configuration files backed up
- [ ] Encryption keys backed up securely (separate from data)
- [ ] Backup schedule automated
- [ ] Backup tested (restore procedure verified)
- [ ] Disaster recovery runbook exists
- [ ] Backup stored off-host (not only on same disk)

---

## Phase 6 — Data Lifecycle

**Goal:** Check retention policies and growth management.

```bash
# Data retention policies
grep -rn 'retention\|expire\|ttl\|max_age\|cleanup\|prune' src/ config/ --include='*.rs' --include='*.yaml' | head -20

# Data growth estimate
# How many records per day? What's the storage growth rate?
grep -rn 'INSERT' src/db/ --include='*.rs' | head -5

# Vector store collection sizes
curl -sf http://localhost:6333/collections 2>/dev/null | jq '.result.collections[] | {name, points_count}' 2>/dev/null

# Log file growth
ls -lh data/logs/ 2>/dev/null

# Database file sizes (if accessible)
ls -lh data/*.db data/**/*.db 2>/dev/null
```

### Lifecycle Checklist

- [ ] Data history has retention policy (or unlimited with rationale)
- [ ] Vector store collections have documented growth expectations
- [ ] Temporary data cleaned up (stale sessions, expired tokens)
- [ ] Audit logs have retention period
- [ ] Log rotation configured
- [ ] Disk usage monitoring in place (alert before full)

---

## Configuration

This instrument reads project-specific paths from `project-profile.yaml` in the target project root. If a profile field is absent, the default from the profile schema applies. Instrument-specific thresholds remain in this instrument's `config.yaml`.

```yaml
thresholds:
  schema:
    doc_alignment_percent: 90
    max_undocumented_tables: 3
    idempotent_migrations: 100
  classification:
    confidential_restricted_encrypted: true
    restricted_audit_trail: true
    no_confidential_in_public_db: true
  backup:
    all_dbs_covered: true
    schedule_automated: true
    restore_tested: true
  lifecycle:
    retention_policy_exists: true
    cleanup_mechanisms: true

scope:
  db_dir: src/db/
  schema_docs: docs/schema-map.md
  config_dir: config/
  backup_scripts: infra/scripts/
  dr_runbook: docs/operations/disaster-recovery-runbook.md
  vector_store_url: "http://localhost:6333"
```

---

## Output

Reports are written to `output/YYYY-MM-DD_{project_name}/DA{n}-data.md` (see `qualitoscope/config.yaml` for `project_name`).

---

## Run History

| Run | Date | Trigger | Report |
|-----|------|---------|--------|
| DA1 | _pending_ | Initial baseline | — |

## License

Part of [qual-gate](https://github.com/Nelvradia/qual-gate). Licensed under [Apache 2.0](../../LICENSE).
