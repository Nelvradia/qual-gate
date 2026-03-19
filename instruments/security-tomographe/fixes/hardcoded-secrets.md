---
title: "Fix: Hardcoded Secrets"
status: current
last-updated: 2026-03-19
instrument: security-tomographe
severity-range: "Critical"
---

# Fix: Hardcoded Secrets

## What this means

A secret value — API key, password, token, private key, or connection string — is embedded
directly in source code, configuration files tracked by git, or build artifacts. This is a
critical finding because anyone with read access to the repository (including CI logs, container
images, or backups) can extract the secret and use it to impersonate your service, access
protected resources, or escalate privileges. Secrets committed to git history persist even after
the line is deleted, because git retains all prior commits indefinitely.

## How to fix

### Step 1: Rotate the exposed secret immediately

Before cleaning the repository, **assume the secret is compromised.** Rotate it at the source:

- API keys: revoke and regenerate in the provider's dashboard.
- Passwords: change the password on the target system.
- Tokens: invalidate the token and issue a new one.
- Private keys: generate a new keypair and update all systems that trust the old public key.

Do not skip this step. Cleaning git history without rotating is security theatre.

### Step 2: Remove the secret from the codebase

Replace hardcoded values with environment variable lookups or secret manager references (see
language-specific examples below), then commit the fix.

### Step 3: Clean git history

Even after the secret is removed in a new commit, it remains in git history. Use one of these
tools to rewrite history:

```bash
# Option A: git-filter-repo (recommended, faster, maintained)
pip install git-filter-repo

# Remove a specific file from all history
git filter-repo --invert-paths --path config/secrets.yaml

# Replace a specific string across all history
git filter-repo --replace-text <(echo "AKIAIOSFODNN7EXAMPLE==>REDACTED")

# Option B: BFG Repo-Cleaner (simpler for bulk secret removal)
# Download from https://rtyley.github.io/bfg-repo-cleaner/
java -jar bfg.jar --replace-text passwords.txt repo.git
```

**After rewriting history:**

```bash
# Force-push all branches (coordinate with your team first)
git push --force --all
git push --force --tags

# All team members must re-clone or reset their local repos
```

### Python

**Load secrets from environment variables:**

```python
import os

# Direct environment variable lookup
api_key = os.environ["API_KEY"]  # Raises KeyError if missing — fail loud

# With a default for optional config (never default secrets)
debug_mode = os.environ.get("DEBUG", "false")
```

**Use python-dotenv for local development:**

```python
# .env (add to .gitignore — never commit this file)
# API_KEY=sk-abc123
# DATABASE_URL=postgresql://user:pass@localhost/db

from dotenv import load_dotenv
import os

load_dotenv()  # Reads .env into os.environ

api_key = os.environ["API_KEY"]
```

**Pydantic settings for structured config:**

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    api_key: str
    database_url: str
    debug: bool = False

    model_config = {"env_file": ".env"}

settings = Settings()  # Validates types, fails fast on missing values
```

### Rust

**Use `std::env` and the `dotenvy` crate:**

```rust
// Cargo.toml
// [dependencies]
// dotenvy = "0.15"

use std::env;

fn main() {
    // Load .env file for local development (optional in production)
    dotenvy::dotenv().ok();

    let api_key = env::var("API_KEY")
        .expect("API_KEY must be set");

    let db_url = env::var("DATABASE_URL")
        .expect("DATABASE_URL must be set");
}
```

**Compile-time env vars (for build metadata only, never secrets):**

```rust
// This bakes the value into the binary — do NOT use for secrets
let version = env!("CARGO_PKG_VERSION");
```

### TypeScript

**Use the `dotenv` package:**

```typescript
// .env (add to .gitignore)
// API_KEY=sk-abc123

import * as dotenv from "dotenv";
dotenv.config();

const apiKey = process.env.API_KEY;
if (!apiKey) {
  throw new Error("API_KEY environment variable is required");
}
```

**Type-safe config with validation:**

```typescript
import { z } from "zod";
import * as dotenv from "dotenv";

dotenv.config();

const envSchema = z.object({
  API_KEY: z.string().min(1),
  DATABASE_URL: z.string().url(),
  PORT: z.coerce.number().default(3000),
});

// Throws a descriptive error if validation fails
const env = envSchema.parse(process.env);
```

### Go

**Use `os.Getenv` and `godotenv`:**

```go
package main

import (
    "fmt"
    "log"
    "os"

    "github.com/joho/godotenv"
)

func main() {
    // Load .env for local dev (ignore error in production)
    _ = godotenv.Load()

    apiKey := os.Getenv("API_KEY")
    if apiKey == "" {
        log.Fatal("API_KEY environment variable is required")
    }

    dbURL := os.Getenv("DATABASE_URL")
    if dbURL == "" {
        log.Fatal("DATABASE_URL environment variable is required")
    }

    fmt.Println("Configuration loaded successfully")
}
```

### General

**Secret manager integration (production):**

For production systems, environment variables are a minimum. Prefer a dedicated secret manager:

- **HashiCorp Vault:** Centralised secret storage with audit logging, dynamic secrets,
  automatic rotation, and fine-grained access policies.
- **AWS Secrets Manager / Azure Key Vault / GCP Secret Manager:** Cloud-native options with
  IAM-based access control.
- **Kubernetes Secrets + External Secrets Operator:** Syncs secrets from a vault into k8s
  pods without exposing them in manifests.

**Template for `.env.example` (commit this, not `.env`):**

```bash
# Copy to .env and fill in real values. Never commit .env itself.
API_KEY=
DATABASE_URL=
JWT_SECRET=
SMTP_PASSWORD=
```

**`.gitignore` entries (mandatory):**

```gitignore
# Secret and environment files
.env
.env.*
!.env.example
*.pem
*.key
*credentials*
*secret*
```

## Prevention

**Pre-commit scanning with gitleaks:**

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/gitleaks/gitleaks
    rev: v8.21.0
    hooks:
      - id: gitleaks
```

**CI pipeline enforcement:**

```yaml
# GitLab CI
secret-scan:
  stage: lint
  image: zricethezav/gitleaks:latest
  script:
    - gitleaks detect --source . --verbose --redact
  allow_failure: false
```

**Additional tooling:**

- **truffleHog:** Scans git history for high-entropy strings and known secret patterns.
- **detect-secrets (Yelp):** Maintains a baseline of known false positives, reducing noise.
- **GitHub push protection / GitLab secret detection:** Platform-level scans that block pushes
  containing secrets.

**Process rules:**

- Never pass secrets via CLI arguments — they appear in `ps` output and shell history.
- Never log secrets, even at DEBUG level. Mask them in log output.
- Rotate secrets on a schedule, not just when compromised.
- Use short-lived tokens (e.g., OAuth2 tokens with 1-hour expiry) over long-lived API keys.
- Require code review for any file that configures authentication or secret loading.
