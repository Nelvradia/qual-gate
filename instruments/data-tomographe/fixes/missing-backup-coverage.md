---
title: "Fix: Missing Backup Coverage"
status: current
last-updated: 2026-03-19
instrument: data-tomographe
severity-range: "Major"
---

# Fix: Missing Backup Coverage

## What this means

Your project stores persistent data (databases, object storage, configuration state) but lacks
a documented and tested backup strategy. Without verified backups, any data loss event — hardware
failure, accidental deletion, ransomware, or a bad migration — becomes permanent. The severity
is Major because while backup gaps do not cause immediate failures, they represent a single point
of irreversible data loss. A backup strategy is only valid if restores are regularly tested;
untested backups are indistinguishable from no backups at all.

## How to fix

### Python

**Automated backup script with verification:**

```python
# scripts/backup_database.py
"""Database backup with integrity verification."""
from __future__ import annotations

import hashlib
import logging
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

BACKUP_DIR = Path("/var/backups/db")
RETENTION_DAYS = 30


def create_backup(database_url: str) -> Path:
    """Create a compressed, timestamped database dump."""
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup_path = BACKUP_DIR / f"backup-{timestamp}.sql.gz"
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)

    result = subprocess.run(
        ["pg_dump", database_url, "--format=custom", "--compress=9"],
        capture_output=True,
        check=True,
    )

    backup_path.write_bytes(result.stdout)
    checksum = hashlib.sha256(result.stdout).hexdigest()
    backup_path.with_suffix(".gz.sha256").write_text(f"{checksum}  {backup_path.name}\n")

    logger.info("Backup created: %s (%d bytes, sha256=%s)", backup_path, len(result.stdout), checksum)
    return backup_path


def verify_backup(backup_path: Path, database_url: str) -> bool:
    """Restore a backup to a temporary database and run basic checks."""
    try:
        subprocess.run(
            ["pg_restore", "--dbname", database_url, "--clean", "--if-exists", str(backup_path)],
            capture_output=True,
            check=True,
        )
        logger.info("Backup restore verification passed: %s", backup_path)
        return True
    except subprocess.CalledProcessError as exc:
        logger.error("Backup restore failed: %s — %s", backup_path, exc.stderr.decode())
        return False


def prune_old_backups(retention_days: int = RETENTION_DAYS) -> int:
    """Delete backups older than retention window."""
    cutoff = datetime.now(timezone.utc).timestamp() - (retention_days * 86400)
    removed = 0
    for f in BACKUP_DIR.glob("backup-*.sql.gz*"):
        if f.stat().st_mtime < cutoff:
            f.unlink()
            removed += 1
    return removed
```

Test restores in CI by calling `verify_backup()` against a disposable test database and
asserting that critical tables exist after restore.

### Rust

**Backup orchestration with process spawning:**

```rust
use std::process::Command;
use std::path::PathBuf;
use chrono::Utc;
use anyhow::{Context, Result};

/// Create a compressed PostgreSQL backup.
pub fn create_backup(database_url: &str, backup_dir: &PathBuf) -> Result<PathBuf> {
    std::fs::create_dir_all(backup_dir)
        .context("create backup directory")?;

    let timestamp = Utc::now().format("%Y%m%dT%H%M%SZ");
    let backup_path = backup_dir.join(format!("backup-{timestamp}.dump"));

    let status = Command::new("pg_dump")
        .args(["--format=custom", "--compress=9", "-f"])
        .arg(&backup_path)
        .arg(database_url)
        .status()
        .context("run pg_dump")?;

    if !status.success() {
        anyhow::bail!("pg_dump exited with status {status}");
    }

    tracing::info!(path = %backup_path.display(), "backup created");
    Ok(backup_path)
}

/// Verify a backup by restoring to a test database.
pub fn verify_backup(backup_path: &PathBuf, test_db_url: &str) -> Result<()> {
    let status = Command::new("pg_restore")
        .args(["--dbname", test_db_url, "--clean", "--if-exists"])
        .arg(backup_path)
        .status()
        .context("run pg_restore")?;

    if !status.success() {
        anyhow::bail!("pg_restore failed for {}", backup_path.display());
    }
    Ok(())
}
```

### TypeScript

**Backup script with S3 upload:**

```typescript
// scripts/backup.ts
import { execSync } from "child_process";
import { createHash } from "crypto";
import { readFileSync, mkdirSync } from "fs";
import { join } from "path";

const BACKUP_DIR = process.env.BACKUP_DIR ?? "/var/backups/db";

function createBackup(databaseUrl: string): string {
  mkdirSync(BACKUP_DIR, { recursive: true });
  const timestamp = new Date().toISOString().replace(/[:.]/g, "");
  const backupPath = join(BACKUP_DIR, `backup-${timestamp}.dump`);

  execSync(`pg_dump --format=custom --compress=9 -f "${backupPath}" "${databaseUrl}"`);

  const content = readFileSync(backupPath);
  const sha256 = createHash("sha256").update(content).digest("hex");
  console.log(`Backup: ${backupPath} (${content.length} bytes, sha256=${sha256})`);
  return backupPath;
}

function verifyBackup(backupPath: string, testDbUrl: string): void {
  execSync(`pg_restore --dbname "${testDbUrl}" --clean --if-exists "${backupPath}"`);
  console.log(`Restore verification passed: ${backupPath}`);
}
```

### Go

**Backup with checksum verification:**

```go
package backup

import (
    "crypto/sha256"
    "fmt"
    "os"
    "os/exec"
    "path/filepath"
    "time"
)

// Create produces a compressed database dump and returns its path.
func Create(databaseURL, backupDir string) (string, error) {
    if err := os.MkdirAll(backupDir, 0o750); err != nil {
        return "", fmt.Errorf("create backup dir: %w", err)
    }

    timestamp := time.Now().UTC().Format("20060102T150405Z")
    path := filepath.Join(backupDir, fmt.Sprintf("backup-%s.dump", timestamp))

    cmd := exec.Command("pg_dump", "--format=custom", "--compress=9",
        "-f", path, databaseURL)
    if out, err := cmd.CombinedOutput(); err != nil {
        return "", fmt.Errorf("pg_dump: %w\n%s", err, out)
    }

    data, err := os.ReadFile(path)
    if err != nil {
        return "", fmt.Errorf("read backup for checksum: %w", err)
    }
    checksum := fmt.Sprintf("%x", sha256.Sum256(data))
    checksumPath := path + ".sha256"
    _ = os.WriteFile(checksumPath, []byte(checksum+"  "+filepath.Base(path)+"\n"), 0o640)

    return path, nil
}

// Verify restores a backup to a test database to confirm integrity.
func Verify(backupPath, testDBURL string) error {
    cmd := exec.Command("pg_restore", "--dbname", testDBURL,
        "--clean", "--if-exists", backupPath)
    if out, err := cmd.CombinedOutput(); err != nil {
        return fmt.Errorf("pg_restore: %w\n%s", err, out)
    }
    return nil
}
```

### General

**Backup strategy checklist:**

1. **What to back up:** Databases, object storage (S3/MinIO buckets), configuration files,
   secrets vault exports, and any stateful volumes.
2. **Frequency:** Align with your Recovery Point Objective (RPO). If you can tolerate losing
   1 hour of data, back up at least hourly.
3. **Retention:** Define a retention policy (e.g., 7 daily, 4 weekly, 12 monthly). Automate
   pruning — unbounded retention fills disks.
4. **Storage location:** Backups must be in a different failure domain than the primary data.
   At minimum, a different machine. Ideally, a different region or provider.
5. **Encryption:** Encrypt backups at rest. Use `gpg` or the storage provider's server-side
   encryption. Protect encryption keys separately from backups.

**Point-in-time recovery (PITR):** For PostgreSQL, enable WAL archiving
(`wal_level = replica`, `archive_mode = on`) for continuous backup that allows recovery to
any point in time, not just the last dump.

**Restore testing cadence:** Weekly automated restore in CI, monthly full restore to staging,
quarterly disaster recovery simulation timed against your RTO.

## Prevention

**CI pipeline — backup verification:**

```yaml
# GitLab CI — weekly schedule
backup-verify:
  stage: test
  rules:
    - if: $CI_PIPELINE_SOURCE == "schedule"
  services:
    - postgres:16-alpine
  variables:
    POSTGRES_DB: restore_test
    POSTGRES_USER: test
    POSTGRES_PASSWORD: test
  script:
    - LATEST=$(ls -t /var/backups/db/backup-*.dump | head -1)
    - pg_restore --dbname "postgresql://test:test@postgres/restore_test"
        --clean --if-exists "$LATEST"
    - psql "postgresql://test:test@postgres/restore_test"
        -c "SELECT count(*) FROM users" | grep -E "^[0-9]+"
  allow_failure: false
```

**Backup monitoring alerts:**

- Alert if no backup was created in the last `RPO + margin` window.
- Alert if backup size changes more than 50% from the previous backup (could indicate
  data loss or corruption).
- Alert if checksum verification fails.
- Track backup duration — a sudden increase may signal disk or network issues.

**Documentation requirements:**

Every project with persistent data must have a `docs/backup-restore.md` covering:

- What is backed up and what is not
- Backup frequency and retention policy
- RPO and RTO targets
- Step-by-step restore procedure (tested, not theoretical)
- Contact/escalation path for data loss incidents
