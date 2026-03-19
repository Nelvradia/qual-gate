---
title: "Fix: Missing Input Validation"
status: current
last-updated: 2026-03-19
instrument: security-tomographe
severity-range: "Critical–Major"
---

# Fix: Missing Input Validation

## What this means

User-supplied input reaches application logic, database queries, or rendered output without
validation or sanitisation. This opens the door to injection attacks — SQL injection, cross-site
scripting (XSS), command injection, path traversal, and more. Missing input validation is
consistently in the OWASP Top 10 and remains the most exploited class of vulnerability in web
applications. Every input boundary (HTTP request, file upload, CLI argument, message queue payload)
must validate data before processing.

## How to fix

### Python

**Pydantic for request validation (FastAPI):**

```python
from __future__ import annotations

import re
from typing import Annotated

from pydantic import BaseModel, Field, field_validator


class CreateUserRequest(BaseModel):
    """Validated user creation payload."""

    username: Annotated[str, Field(min_length=3, max_length=30, pattern=r"^[a-zA-Z0-9_]+$")]
    email: Annotated[str, Field(max_length=254)]
    age: Annotated[int, Field(ge=13, le=150)]

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        # Basic structural check — use a dedicated library for full RFC 5322
        if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", v):
            raise ValueError("Invalid email format")
        return v.lower().strip()
```

**SQLAlchemy parameterised queries (prevent SQL injection):**

```python
from sqlalchemy import text

# WRONG — vulnerable to SQL injection
# db.execute(f"SELECT * FROM users WHERE name = '{user_input}'")

# CORRECT — parameterised query
result = db.execute(
    text("SELECT * FROM users WHERE name = :name"),
    {"name": user_input},
)
```

**Bleach for HTML sanitisation (prevent stored XSS):**

```python
import bleach

# Strip all HTML tags
clean_text = bleach.clean(user_input, tags=[], strip=True)

# Allow limited safe tags
clean_html = bleach.clean(
    user_input,
    tags=["b", "i", "em", "strong", "a", "p"],
    attributes={"a": ["href", "title"]},
    protocols=["https"],
    strip=True,
)
```

**Command injection prevention:**

```python
import shlex
import subprocess

# WRONG — shell injection via user_input
# subprocess.run(f"convert {user_input} output.png", shell=True)

# CORRECT — pass arguments as list, never use shell=True with user input
subprocess.run(
    ["convert", user_input, "output.png"],
    check=True,
    timeout=30,
)
```

### Rust

**sqlx compile-time checked queries:**

```rust
use sqlx::PgPool;

// sqlx::query! macro checks the query against the database schema at compile time.
// Parameters are always bound safely — SQL injection is structurally impossible.
async fn get_user(pool: &PgPool, username: &str) -> Result<Option<User>, sqlx::Error> {
    sqlx::query_as!(
        User,
        "SELECT id, username, email FROM users WHERE username = $1",
        username
    )
    .fetch_optional(pool)
    .await
}
```

**validator crate for struct validation:**

```rust
use validator::Validate;

#[derive(Debug, Validate, serde::Deserialize)]
pub struct CreateUserRequest {
    #[validate(length(min = 3, max = 30), regex(path = "RE_USERNAME"))]
    pub username: String,

    #[validate(email)]
    pub email: String,

    #[validate(range(min = 13, max = 150))]
    pub age: u8,
}

lazy_static::lazy_static! {
    static ref RE_USERNAME: regex::Regex = regex::Regex::new(r"^[a-zA-Z0-9_]+$").unwrap();
}

// In your handler:
async fn create_user(payload: web::Json<CreateUserRequest>) -> impl Responder {
    if let Err(errors) = payload.validate() {
        return HttpResponse::BadRequest().json(errors);
    }
    // proceed with validated data
}
```

**Path traversal prevention:**

```rust
use std::path::{Path, PathBuf};

/// Resolve a user-supplied filename within a safe base directory.
/// Returns None if the resolved path escapes the base.
fn safe_path(base: &Path, user_filename: &str) -> Option<PathBuf> {
    let candidate = base.join(user_filename);
    let resolved = candidate.canonicalize().ok()?;
    if resolved.starts_with(base.canonicalize().ok()?) {
        Some(resolved)
    } else {
        None // path traversal attempt
    }
}
```

### TypeScript

**Zod for schema validation:**

```typescript
import { z } from "zod";

const CreateUserSchema = z.object({
  username: z
    .string()
    .min(3)
    .max(30)
    .regex(/^[a-zA-Z0-9_]+$/, "Username must be alphanumeric"),
  email: z.string().email().max(254).transform((v) => v.toLowerCase().trim()),
  age: z.number().int().min(13).max(150),
});

type CreateUserInput = z.infer<typeof CreateUserSchema>;

// Express handler
app.post("/users", (req, res) => {
  const result = CreateUserSchema.safeParse(req.body);
  if (!result.success) {
    return res.status(400).json({ errors: result.error.flatten() });
  }
  const validated: CreateUserInput = result.data;
  // proceed with validated data
});
```

**Prepared statements (prevent SQL injection):**

```typescript
import pg from "pg";

const pool = new pg.Pool();

// WRONG — string interpolation in SQL
// await pool.query(`SELECT * FROM users WHERE name = '${userInput}'`);

// CORRECT — parameterised query
const result = await pool.query(
  "SELECT * FROM users WHERE name = $1",
  [userInput]
);
```

**DOMPurify for XSS prevention (browser or server-side with jsdom):**

```typescript
import DOMPurify from "dompurify";
import { JSDOM } from "jsdom";

const window = new JSDOM("").window;
const purify = DOMPurify(window);

const cleanHtml = purify.sanitize(userInput, {
  ALLOWED_TAGS: ["b", "i", "em", "strong", "a", "p"],
  ALLOWED_ATTR: ["href", "title"],
});
```

### Go

**go-playground/validator for struct validation:**

```go
package main

import (
    "net/http"
    "github.com/go-playground/validator/v10"
)

var validate = validator.New()

type CreateUserRequest struct {
    Username string `json:"username" validate:"required,min=3,max=30,alphanum"`
    Email    string `json:"email" validate:"required,email,max=254"`
    Age      int    `json:"age" validate:"required,min=13,max=150"`
}

func createUserHandler(w http.ResponseWriter, r *http.Request) {
    var req CreateUserRequest
    if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
        http.Error(w, "invalid JSON", http.StatusBadRequest)
        return
    }
    if err := validate.Struct(req); err != nil {
        http.Error(w, err.Error(), http.StatusBadRequest)
        return
    }
    // proceed with validated data
}
```

**Parameterised database/sql queries:**

```go
// WRONG — vulnerable to SQL injection
// db.Query("SELECT * FROM users WHERE name = '" + userInput + "'")

// CORRECT — parameterised query
row := db.QueryRowContext(ctx,
    "SELECT id, username, email FROM users WHERE username = $1",
    userInput,
)
```

**Path traversal prevention:**

```go
func safePath(baseDir, userFilename string) (string, error) {
    candidate := filepath.Join(baseDir, userFilename)
    resolved, err := filepath.Abs(candidate)
    if err != nil {
        return "", fmt.Errorf("resolving path: %w", err)
    }
    absBase, _ := filepath.Abs(baseDir)
    if !strings.HasPrefix(resolved, absBase+string(filepath.Separator)) {
        return "", fmt.Errorf("path traversal attempt: %s", userFilename)
    }
    return resolved, nil
}
```

### General

**OWASP input validation principles:**

1. **Validate on the server.** Client-side validation improves UX but provides zero security.
   An attacker bypasses it trivially.
2. **Allowlist over denylist.** Define what is allowed (alphanumeric, max length, known enum
   values) rather than trying to block known-bad patterns. Denylists always have gaps.
3. **Validate at every trust boundary.** Input from HTTP requests, message queues, file uploads,
   environment variables, and even internal service calls must be validated.
4. **Reject, don't sanitise, where possible.** Sanitisation can introduce subtle bugs.
   Rejecting invalid input with a clear error is safer and easier to reason about.
5. **Use typed parsing.** Parse input into typed structures (int, enum, datetime) rather than
   passing raw strings through the application.
6. **Limit payload size.** Set max request body size at the web server/framework level to prevent
   denial-of-service via oversized payloads.

## Prevention

- **Static analysis:** Use `semgrep` or `bandit` (Python) to detect string-interpolated SQL
  queries and shell=True subprocess calls in CI.
- **SAST rules:** Enable SQL injection and XSS rules in your SAST scanner. Most support custom
  rules for project-specific patterns.
- **API schema enforcement:** Use OpenAPI schemas with strict validation. Generate server stubs
  from the schema so validation is structural, not manual.
- **Fuzz testing:** Run `hypothesis` (Python), `cargo-fuzz` (Rust), or `go-fuzz` against
  input-handling functions to discover edge cases.
- **Content-Security-Policy header:** Deploy CSP headers to mitigate XSS even if sanitisation
  fails: `Content-Security-Policy: default-src 'self'; script-src 'self'`.
- **WAF rules:** Deploy a Web Application Firewall (ModSecurity, AWS WAF, Cloudflare) with
  OWASP Core Rule Set as a defence-in-depth layer.
