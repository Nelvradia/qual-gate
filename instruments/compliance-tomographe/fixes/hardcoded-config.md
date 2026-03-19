---
title: "Fix: Hardcoded Configuration"
status: current
last-updated: 2026-03-19
instrument: compliance-tomographe
severity-range: "Minor–Major"
---

# Fix: Hardcoded Configuration

## What this means

Your codebase contains configuration values embedded directly in source code -- database URLs,
API endpoints, feature flags, port numbers, timeouts, or credentials. Hardcoded configuration
violates the twelve-factor app methodology, makes deployment across environments (dev, staging,
production) error-prone, and creates security risks when secrets are committed to version control.
Even non-secret configuration (ports, hostnames, thresholds) becomes a maintenance burden when
it requires code changes and redeployment to adjust.

## How to fix

### Python

**Environment variables with validation:**

```python
from __future__ import annotations

import os
from dataclasses import dataclass, field


@dataclass(frozen=True)
class AppConfig:
    """Application configuration loaded from environment variables."""

    db_host: str = field(default_factory=lambda: os.environ["DB_HOST"])
    db_port: int = field(
        default_factory=lambda: int(os.environ.get("DB_PORT", "5432"))
    )
    log_level: str = field(
        default_factory=lambda: os.environ.get("LOG_LEVEL", "INFO")
    )
    max_retries: int = field(
        default_factory=lambda: int(os.environ.get("MAX_RETRIES", "3"))
    )

    def __post_init__(self) -> None:
        if self.db_port < 1 or self.db_port > 65535:
            raise ValueError(f"DB_PORT must be 1-65535, got {self.db_port}")
        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if self.log_level not in valid_levels:
            raise ValueError(
                f"LOG_LEVEL must be one of {valid_levels}, got {self.log_level}"
            )
```

**Alternative: pydantic-settings** provides validation, `.env` file support, and typed config
in fewer lines. Use `BaseSettings` with `env_prefix` for namespaced env vars.

### Rust

**Using environment variables with typed config:**

```rust
use std::env;
use std::net::SocketAddr;

#[derive(Debug, Clone)]
struct AppConfig {
    db_url: String,
    listen_addr: SocketAddr,
    max_connections: u32,
    log_level: String,
}

impl AppConfig {
    fn from_env() -> anyhow::Result<Self> {
        Ok(Self {
            db_url: env::var("DATABASE_URL")
                .context("DATABASE_URL must be set")?,
            listen_addr: env::var("LISTEN_ADDR")
                .unwrap_or_else(|_| "0.0.0.0:8080".to_string())
                .parse()
                .context("LISTEN_ADDR must be a valid socket address")?,
            max_connections: env::var("MAX_CONNECTIONS")
                .unwrap_or_else(|_| "100".to_string())
                .parse()
                .context("MAX_CONNECTIONS must be a positive integer")?,
            log_level: env::var("LOG_LEVEL")
                .unwrap_or_else(|_| "info".to_string()),
        })
    }
}
```

**Using the `config` crate for layered configuration:**

```rust
use config::{Config, Environment, File};
use serde::Deserialize;

#[derive(Debug, Deserialize)]
struct AppConfig {
    database: DatabaseConfig,
    server: ServerConfig,
}

#[derive(Debug, Deserialize)]
struct DatabaseConfig {
    url: String,
    max_connections: u32,
}

#[derive(Debug, Deserialize)]
struct ServerConfig {
    host: String,
    port: u16,
}

fn load_config() -> anyhow::Result<AppConfig> {
    let config = Config::builder()
        // Start with defaults
        .add_source(File::with_name("config/default"))
        // Layer environment-specific file
        .add_source(
            File::with_name(&format!(
                "config/{}",
                std::env::var("APP_ENV").unwrap_or_else(|_| "dev".into())
            ))
            .required(false),
        )
        // Override with environment variables (APP_DATABASE__URL, etc.)
        .add_source(Environment::with_prefix("APP").separator("__"))
        .build()?;

    config.try_deserialize().map_err(Into::into)
}
```

### TypeScript

```typescript
import { z } from "zod";

const ConfigSchema = z.object({
  DB_HOST: z.string().min(1),
  DB_PORT: z.coerce.number().int().min(1).max(65535).default(5432),
  LOG_LEVEL: z
    .enum(["debug", "info", "warn", "error"])
    .default("info"),
  API_TIMEOUT_MS: z.coerce.number().positive().default(30000),
  FEATURE_NEW_UI: z
    .enum(["true", "false"])
    .transform((v) => v === "true")
    .default("false"),
});

export type AppConfig = z.infer<typeof ConfigSchema>;

export function loadConfig(): AppConfig {
  const result = ConfigSchema.safeParse(process.env);
  if (!result.success) {
    const formatted = result.error.issues
      .map((i) => `  ${i.path.join(".")}: ${i.message}`)
      .join("\n");
    throw new Error(`Invalid configuration:\n${formatted}`);
  }
  return result.data;
}
```

### Go

```go
package config

import (
    "fmt"
    "os"
    "strconv"
)

// AppConfig holds all application configuration.
type AppConfig struct {
    DBHost         string
    DBPort         int
    LogLevel       string
    MaxRetries     int
    TimeoutSeconds int
}

// Load reads configuration from environment variables with defaults and
// validation.
func Load() (*AppConfig, error) {
    cfg := &AppConfig{
        DBHost:         getEnvOrDefault("DB_HOST", ""),
        LogLevel:       getEnvOrDefault("LOG_LEVEL", "info"),
    }

    if cfg.DBHost == "" {
        return nil, fmt.Errorf("DB_HOST environment variable is required")
    }

    var err error
    cfg.DBPort, err = getEnvInt("DB_PORT", 5432)
    if err != nil {
        return nil, fmt.Errorf("invalid DB_PORT: %w", err)
    }

    cfg.MaxRetries, err = getEnvInt("MAX_RETRIES", 3)
    if err != nil {
        return nil, fmt.Errorf("invalid MAX_RETRIES: %w", err)
    }

    return cfg, nil
}

// getEnvOrDefault returns the env var value or the fallback.
func getEnvOrDefault(key, fallback string) string {
    if val, ok := os.LookupEnv(key); ok { return val }
    return fallback
}

// getEnvInt parses an env var as int, returning fallback if unset.
func getEnvInt(key string, fallback int) (int, error) {
    val, ok := os.LookupEnv(key)
    if !ok { return fallback, nil }
    return strconv.Atoi(val)
}
```

### General

**Twelve-factor app configuration principles:**

1. **Store config in the environment** -- not in code. Env vars for deployment-specific values.
2. **Separate config from code** -- same artefact runs in dev, staging, and production.
3. **Layer configuration** -- defaults in code, overridden by config files, overridden by env
   vars. Environment variables always win.
4. **Validate early** -- parse all config at startup. Fail fast with clear error messages.
5. **Never commit secrets** -- use secret managers (Vault, CI/CD variables), never source code.

**Must externalise:** DB URLs, API endpoints, credentials, tokens, ports, feature flags.

**Acceptable in code:** Algorithmic constants (pi, gravity), protocol-mandated values (HTTP
status codes), internal data structure sizes.

## Prevention

**CI-enforceable checks:**

```yaml
# GitLab CI example
hardcoded-config-check:
  stage: lint
  script:
    # Scan for common hardcoded patterns
    - |
      grep -rn --include="*.py" --include="*.rs" --include="*.ts" --include="*.go" \
        -E '(localhost|127\.0\.0\.1|0\.0\.0\.0):[0-9]+' src/ \
        && echo "ERROR: Hardcoded host:port found" && exit 1 || true
    # Check for hardcoded credentials patterns
    - |
      grep -rn --include="*.py" --include="*.rs" --include="*.ts" --include="*.go" \
        -iE '(password|secret|api_key|token)\s*=\s*"[^"]{4,}"' src/ \
        && echo "ERROR: Possible hardcoded credential" && exit 1 || true
  rules:
    - if: $CI_PIPELINE_SOURCE == "merge_request_event"
```

**Tools:**

- **detect-secrets** (Python): Pre-commit hook that scans for accidentally committed secrets.
- **gitleaks**: Scans git history for secrets and credentials.
- **trufflehog**: Deep git history scanning for high-entropy strings and known secret formats.

**Process:**

- Require a `.env.example` file documenting every environment variable the application expects,
  with placeholder values and descriptions.
- Add `.env` to `.gitignore` on project creation. Never commit real `.env` files.
- Review all string literals in MRs for potential externalisation candidates.
