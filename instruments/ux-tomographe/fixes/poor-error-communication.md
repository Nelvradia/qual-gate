---
title: "Fix: Poor Error Communication"
status: current
last-updated: 2026-03-19
instrument: ux-tomographe
severity-range: "Minor--Major"
---

# Fix: Poor Error Communication

## What this means

Your application presents errors to users in ways that are unhelpful, confusing, or invisible.
This includes raw stack traces or HTTP status codes shown to end users, generic "something went
wrong" messages without actionable guidance, missing error states in UI components (blank screens
on failure), or errors that disappear before users can read them. Minor findings are unclear
wording or inconsistent error formatting. Major findings are silent failures where the user has
no indication that an operation failed, or error messages that expose internal system details
(database names, file paths, internal IPs) which are also a security concern.

## How to fix

### Python

**Structure API error responses consistently:**

```python
from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse


class ErrorCode(StrEnum):
    """Application-level error codes — stable identifiers clients can match on."""

    VALIDATION_ERROR = "VALIDATION_ERROR"
    NOT_FOUND = "NOT_FOUND"
    RATE_LIMITED = "RATE_LIMITED"
    INTERNAL_ERROR = "INTERNAL_ERROR"
    UNAUTHORIZED = "UNAUTHORIZED"


@dataclass
class ErrorResponse:
    """Consistent error envelope for all API responses."""

    code: ErrorCode
    message: str  # Human-readable, user-safe
    details: dict[str, Any] | None = None  # Optional structured context

    def to_dict(self) -> dict[str, Any]:
        result = {"code": self.code, "message": self.message}
        if self.details:
            result["details"] = self.details
        return {"error": result}


app = FastAPI()


@app.exception_handler(HTTPException)
async def http_exception_handler(
    request: Request,
    exc: HTTPException,
) -> JSONResponse:
    """Map HTTP exceptions to user-friendly error responses."""
    error_map = {
        400: ErrorResponse(
            code=ErrorCode.VALIDATION_ERROR,
            message="The request contains invalid data. Please check your input.",
            details={"hint": str(exc.detail)},
        ),
        404: ErrorResponse(
            code=ErrorCode.NOT_FOUND,
            message="The requested resource could not be found.",
        ),
        429: ErrorResponse(
            code=ErrorCode.RATE_LIMITED,
            message="Too many requests. Please wait a moment and try again.",
        ),
    }

    error = error_map.get(
        exc.status_code,
        ErrorResponse(
            code=ErrorCode.INTERNAL_ERROR,
            message="An unexpected error occurred. Please try again later.",
        ),
    )
    return JSONResponse(status_code=exc.status_code, content=error.to_dict())


@app.exception_handler(Exception)
async def unhandled_exception_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    """Catch-all: never expose internal details to the user."""
    import logging

    logger = logging.getLogger(__name__)
    logger.exception("Unhandled exception on %s %s", request.method, request.url.path)

    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            code=ErrorCode.INTERNAL_ERROR,
            message="An unexpected error occurred. Please try again later.",
        ).to_dict(),
    )
```

**Validation error messages that help users fix the problem:**

```python
from pydantic import BaseModel, field_validator


class CreateProjectRequest(BaseModel):
    name: str
    budget_hours: float

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError(
                "Project name cannot be empty. "
                "Please provide a descriptive name (e.g., 'Q2 Dashboard Redesign')."
            )
        if len(v) > 100:
            raise ValueError(
                f"Project name is {len(v)} characters. "
                "Maximum length is 100 characters."
            )
        return v.strip()

    @field_validator("budget_hours")
    @classmethod
    def budget_positive(cls, v: float) -> float:
        if v <= 0:
            raise ValueError(
                "Budget must be a positive number of hours (e.g., 40.0). "
                f"Received: {v}"
            )
        return v
```

### Rust

**Define user-facing error types with clear messages:**

```rust
use std::fmt;

/// Errors that can be presented to end users.
/// Internal details are logged separately — never included in the display message.
#[derive(Debug)]
pub enum UserError {
    NotFound { resource: &'static str },
    ValidationFailed { field: String, reason: String },
    RateLimited { retry_after_secs: u64 },
    Unauthorized,
    Internal,
}

impl fmt::Display for UserError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::NotFound { resource } => {
                write!(f, "The requested {resource} could not be found.")
            }
            Self::ValidationFailed { field, reason } => {
                write!(f, "Invalid value for '{field}': {reason}")
            }
            Self::RateLimited { retry_after_secs } => {
                write!(
                    f,
                    "Too many requests. Please wait {retry_after_secs} seconds \
                     and try again."
                )
            }
            Self::Unauthorized => {
                write!(f, "You are not authorised to perform this action.")
            }
            Self::Internal => {
                write!(
                    f,
                    "An unexpected error occurred. Please try again later."
                )
            }
        }
    }
}

/// Convert internal errors to user-safe errors at the boundary.
/// Log the internal error, return the sanitised version.
impl From<sqlx::Error> for UserError {
    fn from(err: sqlx::Error) -> Self {
        tracing::error!(error = %err, "Database error");
        Self::Internal
    }
}
```

**Axum error response integration:**

```rust
use axum::{http::StatusCode, response::IntoResponse, Json};
use serde::Serialize;

#[derive(Serialize)]
struct ErrorBody {
    code: &'static str,
    message: String,
}

impl IntoResponse for UserError {
    fn into_response(self) -> axum::response::Response {
        let (status, code) = match &self {
            UserError::NotFound { .. } => (StatusCode::NOT_FOUND, "NOT_FOUND"),
            UserError::ValidationFailed { .. } => {
                (StatusCode::BAD_REQUEST, "VALIDATION_ERROR")
            }
            UserError::RateLimited { .. } => {
                (StatusCode::TOO_MANY_REQUESTS, "RATE_LIMITED")
            }
            UserError::Unauthorized => (StatusCode::UNAUTHORIZED, "UNAUTHORIZED"),
            UserError::Internal => {
                (StatusCode::INTERNAL_SERVER_ERROR, "INTERNAL_ERROR")
            }
        };

        (status, Json(ErrorBody { code, message: self.to_string() })).into_response()
    }
}
```

### TypeScript

**React error boundary with user-friendly fallback:**

```tsx
import { Component, type ErrorInfo, type ReactNode } from "react";

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false, error: null };

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, info: ErrorInfo): void {
    // Log to monitoring service — never show raw error to user
    console.error("ErrorBoundary caught:", error, info.componentStack);
    // sendToMonitoring({ error, componentStack: info.componentStack });
  }

  render(): ReactNode {
    if (this.state.hasError) {
      return (
        this.props.fallback ?? (
          <div role="alert" className="error-fallback">
            <h2>Something went wrong</h2>
            <p>
              We encountered an unexpected problem. Please refresh the page
              or try again later.
            </p>
            <button onClick={() => this.setState({ hasError: false, error: null })}>
              Try again
            </button>
          </div>
        )
      );
    }
    return this.props.children;
  }
}

// Usage: wrap sections of the UI, not the entire app
// <ErrorBoundary fallback={<DashboardError />}>
//   <Dashboard />
// </ErrorBoundary>
```

**Toast notification system for transient errors:**

```tsx
import { createContext, useCallback, useContext, useState, type ReactNode } from "react";

type ToastType = "error" | "warning" | "info" | "success";

interface Toast {
  id: string;
  type: ToastType;
  message: string;
  action?: { label: string; onClick: () => void };
}

interface ToastContextValue {
  showToast: (toast: Omit<Toast, "id">) => void;
}

const ToastContext = createContext<ToastContextValue | null>(null);

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const showToast = useCallback((toast: Omit<Toast, "id">) => {
    const id = crypto.randomUUID();
    setToasts((prev) => [...prev, { ...toast, id }]);
    // Auto-dismiss after 8 seconds (enough time to read)
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id));
    }, 8000);
  }, []);

  return (
    <ToastContext.Provider value={{ showToast }}>
      {children}
      <div className="toast-container" role="status" aria-live="polite">
        {toasts.map((t) => (
          <div key={t.id} className={`toast toast-${t.type}`} role="alert">
            <p>{t.message}</p>
            {t.action && (
              <button onClick={t.action.onClick}>{t.action.label}</button>
            )}
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

export function useToast(): ToastContextValue {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error("useToast must be used within ToastProvider");
  return ctx;
}

// Usage in a component:
// const { showToast } = useToast();
// showToast({
//   type: "error",
//   message: "Could not save changes. Please check your connection and try again.",
//   action: { label: "Retry", onClick: handleRetry },
// });
```

**Graceful API error handling in fetch calls:**

```typescript
interface ApiError {
  code: string;
  message: string;
  details?: Record<string, unknown>;
}

async function apiFetch<T>(url: string, options?: RequestInit): Promise<T> {
  const response = await fetch(url, options);

  if (!response.ok) {
    let error: ApiError;
    try {
      const body = await response.json();
      error = body.error;
    } catch {
      error = {
        code: "NETWORK_ERROR",
        message: "Unable to reach the server. Please check your connection.",
      };
    }
    throw error;
  }

  return response.json();
}
```

### General

**Error message writing guidelines:**

Every user-facing error message should answer three questions:

1. **What happened?** (in plain language, no jargon)
2. **Why did it happen?** (if the cause is actionable)
3. **What can the user do about it?** (concrete next step)

| Quality | Example |
|---|---|
| Bad | `Error 500` |
| Bad | `NullPointerException at line 423` |
| Bad | `Something went wrong` |
| Better | `Could not save your changes` |
| Good | `Could not save your changes because the file is too large (52 MB). Maximum size is 25 MB. Reduce the file size and try again.` |

**Error state design checklist:**

- Every component that loads data must have: loading state, empty state, error state.
- Error states must be visually distinct (not just colour — include icon and text).
- Error messages must be dismissible or self-clearing when the user retries.
- Destructive errors (data loss) must require explicit acknowledgement before continuing.
- Network errors should suggest checking connectivity, not blame the user.
- Never show raw exception types, SQL errors, or file paths to end users.

**HTTP status code to user message mapping:**

| Status | User message |
|---|---|
| 400 | "Please check your input and try again." |
| 401 | "Please sign in to continue." |
| 403 | "You don't have permission to access this resource." |
| 404 | "We couldn't find what you're looking for." |
| 408 | "The request timed out. Please try again." |
| 413 | "The file is too large. Maximum size is {limit}." |
| 429 | "Too many requests. Please wait a moment and try again." |
| 500 | "Something went wrong on our end. Please try again later." |
| 503 | "The service is temporarily unavailable. Please try again shortly." |

## Prevention

**Lint rules for error handling:**

```js
// eslint.config.js — catch console.error used as user communication
export default [
  {
    rules: {
      // Force explicit error boundary usage
      "no-console": ["warn", { allow: ["warn"] }],
    },
  },
];
```

**API response schema validation in tests:**

```python
# tests/unit/test_error_responses.py
import pytest
from httpx import AsyncClient

ERROR_SCHEMA_KEYS = {"code", "message"}


@pytest.mark.parametrize(
    "method,path,status",
    [
        ("GET", "/api/projects/nonexistent-id", 404),
        ("POST", "/api/projects", 400),  # empty body
    ],
)
async def test_error_responses_follow_schema(
    client: AsyncClient,
    method: str,
    path: str,
    status: int,
) -> None:
    response = await client.request(method, path)
    assert response.status_code == status, (
        f"Expected {status}, got {response.status_code}"
    )
    body = response.json()
    assert "error" in body, "Error response must have 'error' envelope"
    assert ERROR_SCHEMA_KEYS.issubset(body["error"].keys()), (
        f"Error object missing required keys: {ERROR_SCHEMA_KEYS - body['error'].keys()}"
    )
```

**Storybook stories for error states:**

```tsx
// Card.stories.tsx — every component should have an error story
export const ErrorState: Story = {
  args: {
    error: "Could not load project data. Please try again.",
    onRetry: () => console.log("retry clicked"),
  },
};

export const EmptyState: Story = {
  args: { items: [] },
};
```

**Process rules:**

- Every UI component that makes API calls must implement loading, success, empty, and
  error states. PRs without error states are blocked.
- Error messages must be reviewed by a non-developer (PM, designer, or tech writer) for
  clarity before release.
- Never expose internal identifiers, stack traces, or system paths in user-facing responses.
- Use structured error codes (e.g., `VALIDATION_ERROR`) alongside human messages so clients
  can programmatically handle errors without parsing message text.
- Test error paths in E2E tests: simulate network failures, invalid input, and expired
  sessions.
