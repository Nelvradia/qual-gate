---
title: "Fix: Unauthenticated Endpoint"
status: current
last-updated: 2026-03-19
instrument: security-tomographe
severity-range: "Critical–Major"
---

# Fix: Unauthenticated Endpoint

## What this means

One or more API endpoints are accessible without any authentication. This means any client —
including automated scanners, bots, and malicious actors — can call these endpoints without
proving their identity. Depending on what the endpoint exposes, this can lead to data leaks,
unauthorised actions, resource abuse, or full system compromise. Even "read-only" endpoints
can be dangerous if they expose internal state, user data, or system configuration. The fix
requires adding authentication middleware so that every non-public endpoint verifies the
caller's identity before processing the request.

## How to fix

### Step 1: Audit your endpoint inventory

Before adding auth, catalogue every endpoint and classify it:

| Endpoint | Method | Public? | Justification |
|---|---|---|---|
| `/health` | GET | Yes | Load balancer health check |
| `/api/v1/users` | GET | No | Returns user data |
| `/api/v1/login` | POST | Yes | Auth entry point |
| `/api/v1/orders` | POST | No | Creates resources |

**Rule of thumb:** An endpoint is public only if there is a documented business reason. Default
to private.

### Python

**FastAPI — dependency-based auth:**

```python
from fastapi import Depends, FastAPI, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

app = FastAPI()
security = HTTPBearer()


async def verify_token(
    credentials: HTTPAuthorizationCredentials = Security(security),
) -> str:
    """Validate the Bearer token and return the user identity."""
    token = credentials.credentials
    # Replace with your actual token validation (JWT decode, DB lookup, etc.)
    payload = decode_and_validate_token(token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return payload["sub"]


# Protected endpoint — requires valid token
@app.get("/api/v1/users")
async def list_users(current_user: str = Depends(verify_token)):
    return {"user": current_user, "data": []}


# Public endpoint — no dependency injection
@app.get("/health")
async def health():
    return {"status": "ok"}
```

**Django:** Add a custom middleware class that checks `request.headers.get("Authorization")`
for all `/api/` paths, allowlisting public endpoints like `/api/health`. Return
`JsonResponse({"error": "..."}, status=401)` for missing or invalid tokens.

### Rust

**Axum — middleware layer:**

```rust
use axum::{
    extract::Request,
    http::{header, StatusCode},
    middleware::{self, Next},
    response::Response,
    routing::get,
    Router,
};

async fn require_auth(req: Request, next: Next) -> Result<Response, StatusCode> {
    let auth_header = req
        .headers()
        .get(header::AUTHORIZATION)
        .and_then(|v| v.to_str().ok());

    match auth_header {
        Some(value) if value.starts_with("Bearer ") => {
            let token = &value[7..];
            if validate_token(token).is_ok() {
                Ok(next.run(req).await)
            } else {
                Err(StatusCode::UNAUTHORIZED)
            }
        }
        _ => Err(StatusCode::UNAUTHORIZED),
    }
}

fn app() -> Router {
    // Public routes — no auth middleware
    let public = Router::new()
        .route("/health", get(health_handler));

    // Protected routes — auth middleware applied
    let protected = Router::new()
        .route("/api/v1/users", get(list_users))
        .route("/api/v1/orders", get(list_orders))
        .layer(middleware::from_fn(require_auth));

    Router::new().merge(public).merge(protected)
}
```

**Actix-web:** Use `actix_web_httpauth::middleware::HttpAuthentication::bearer(validator)` and
wrap protected scopes with `.wrap(auth)`. The validator receives a `BearerAuth` extractor and
returns `Ok(req)` or an error.

### TypeScript

**Express — middleware-based auth:**

```typescript
import express, { Request, Response, NextFunction } from "express";

function requireAuth(req: Request, res: Response, next: NextFunction): void {
  const authHeader = req.headers.authorization;

  if (!authHeader?.startsWith("Bearer ")) {
    res.status(401).json({ error: "Authentication required" });
    return;
  }

  const token = authHeader.slice(7);
  const user = validateToken(token);

  if (!user) {
    res.status(401).json({ error: "Invalid or expired token" });
    return;
  }

  // Attach user to request for downstream handlers
  (req as any).user = user;
  next();
}

const app = express();

// Public routes
app.get("/health", (req, res) => res.json({ status: "ok" }));

// Protected routes — apply middleware to the router
const apiRouter = express.Router();
apiRouter.use(requireAuth);
apiRouter.get("/users", (req, res) => res.json({ users: [] }));
apiRouter.post("/orders", (req, res) => res.json({ created: true }));

app.use("/api/v1", apiRouter);
```

**NestJS — guard-based auth:** Implement `CanActivate`, register as a global guard, and use a
`@Public()` decorator (via `SetMetadata`) to opt out specific endpoints. The guard reads the
`Authorization` header, validates the token, and attaches the user to the request. Non-public
endpoints without a valid token receive a 401 automatically.

### Go

**net/http — middleware pattern:**

```go
package main

import (
    "net/http"
    "strings"
)

func requireAuth(next http.Handler) http.Handler {
    return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
        authHeader := r.Header.Get("Authorization")
        if !strings.HasPrefix(authHeader, "Bearer ") {
            http.Error(w, `{"error":"authentication required"}`, http.StatusUnauthorized)
            return
        }

        token := strings.TrimPrefix(authHeader, "Bearer ")
        user, err := validateToken(token)
        if err != nil {
            http.Error(w, `{"error":"invalid token"}`, http.StatusUnauthorized)
            return
        }

        // Store user in request context
        ctx := context.WithValue(r.Context(), userContextKey, user)
        next.ServeHTTP(w, r.WithContext(ctx))
    })
}

func main() {
    mux := http.NewServeMux()

    // Public
    mux.HandleFunc("/health", healthHandler)

    // Protected — wrap with auth middleware
    mux.Handle("/api/v1/users", requireAuth(http.HandlerFunc(listUsers)))
    mux.Handle("/api/v1/orders", requireAuth(http.HandlerFunc(listOrders)))

    http.ListenAndServe(":8080", mux)
}
```

**Gin:** Use `r.Group("/api/v1", authMiddleware())` to apply auth to all routes in the group.
The middleware pattern is identical — check the `Authorization` header, validate the token,
call `c.AbortWithStatusJSON(401, ...)` on failure, or `c.Next()` on success.

### General

**API gateway as a central auth layer:**

If you run multiple backend services, enforce authentication at the API gateway rather than
in each service. This provides a single point of enforcement and audit.

- **Kong:** Use the JWT or OAuth2 plugin to validate tokens before forwarding.
- **Envoy:** Configure JWT authentication in the HTTP connection manager filter.
- **Nginx:** Use `auth_request` to delegate token validation to an auth service.
- **Cloud gateways (AWS API Gateway, Azure APIM):** Built-in JWT/OAuth2 validation policies.

**Endpoint inventory process:**

1. Extract all registered routes from your framework (most frameworks have a CLI command or
   introspection API for this).
2. Compare against your public/private classification.
3. Flag any endpoint without auth middleware as a finding.
4. Repeat this audit on every release — new endpoints must be classified before merge.

## Prevention

**CI enforcement — detect unprotected routes:**

```yaml
# Scan for route definitions without auth middleware
endpoint-auth-audit:
  stage: lint
  script:
    - python scripts/audit_endpoints.py --require-auth --exclude "/health,/ready,/metrics"
  allow_failure: false
```

**Integration test — verify auth rejection:**

```python
# tests/integration/test_auth_enforcement.py
import pytest
import httpx

PROTECTED_ENDPOINTS = [
    ("GET", "/api/v1/users"),
    ("POST", "/api/v1/orders"),
    ("DELETE", "/api/v1/users/1"),
]

@pytest.mark.parametrize("method,path", PROTECTED_ENDPOINTS)
def test_protected_endpoint_rejects_unauthenticated(method, path):
    """Every protected endpoint must return 401 without a valid token."""
    response = httpx.request(method, f"http://localhost:8000{path}")
    assert response.status_code == 401, (
        f"{method} {path} returned {response.status_code} without auth — expected 401"
    )
```

**Process controls:**

- Require auth classification in the MR template for any endpoint change.
- Use an "auth required by default" framework pattern — public endpoints opt out explicitly
  (allowlist), not the other way around (denylist).
- Periodic penetration testing to catch endpoints missed by automated checks.
- Log all unauthenticated access attempts for monitoring and alerting.
