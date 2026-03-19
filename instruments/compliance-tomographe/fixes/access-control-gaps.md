---
title: "Fix: Access Control Gaps"
status: current
last-updated: 2026-03-19
instrument: compliance-tomographe
severity-range: "Major"
---

# Fix: Access Control Gaps

## What this means

Your project has insufficient or missing access controls -- endpoints without authentication,
overly broad permissions, missing role checks, or no separation between user privilege levels.
Access control gaps allow unauthorized users to read, modify, or delete data they should not
have access to. This violates the principle of least privilege and can lead to data breaches,
regulatory penalties (GDPR Art. 32 requires "appropriate technical measures"), and audit
failures. Even internal-only systems need access controls to limit blast radius when credentials
are compromised.

## How to fix

### Step 1: Define roles and permissions

| Role | Description | Typical Permissions |
|---|---|---|
| **anonymous** | Unauthenticated user | Read public resources only |
| **viewer** | Authenticated, read-only | Read own data, list shared resources |
| **editor** | Can modify resources | Create, update own resources |
| **admin** | Full control within scope | Manage users, configure system, delete |
| **superadmin** | Cross-tenant control | System-wide operations, impersonation |

### Python

```python
from __future__ import annotations

import functools
from enum import Enum
from typing import Callable


class Role(Enum):
    ANONYMOUS = 0
    VIEWER = 1
    EDITOR = 2
    ADMIN = 3


class Permission(Enum):
    READ_OWN = "read:own"
    READ_ALL = "read:all"
    WRITE_OWN = "write:own"
    WRITE_ALL = "write:all"
    DELETE_ALL = "delete:all"
    MANAGE_USERS = "manage:users"


ROLE_PERMISSIONS: dict[Role, set[Permission]] = {
    Role.ANONYMOUS: set(),
    Role.VIEWER: {Permission.READ_OWN},
    Role.EDITOR: {Permission.READ_OWN, Permission.WRITE_OWN},
    Role.ADMIN: set(Permission),
}


def require_permission(*permissions: Permission) -> Callable:
    """Decorator that enforces permission checks on route handlers."""

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            user = get_current_user()
            user_permissions = ROLE_PERMISSIONS.get(user.role, set())
            missing = set(permissions) - user_permissions
            if missing:
                raise PermissionError(
                    f"User '{user.id}' lacks: {', '.join(p.value for p in missing)}"
                )
            return func(*args, **kwargs)
        return wrapper
    return decorator


@require_permission(Permission.WRITE_ALL)
def update_user_profile(user_id: str, data: dict) -> None:
    ...
```

### Rust

```rust
use std::collections::HashSet;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum Permission {
    ReadOwn, ReadAll, WriteOwn, WriteAll, DeleteAll, ManageUsers,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Role { Anonymous, Viewer, Editor, Admin }

impl Role {
    pub fn permissions(self) -> HashSet<Permission> {
        match self {
            Role::Anonymous => HashSet::new(),
            Role::Viewer => [Permission::ReadOwn].into(),
            Role::Editor => {
                [Permission::ReadOwn, Permission::WriteOwn].into()
            }
            Role::Admin => {
                [
                    Permission::ReadAll, Permission::WriteAll,
                    Permission::DeleteAll, Permission::ManageUsers,
                ].into()
            }
        }
    }
}

pub fn check_permissions(
    user_role: Role,
    required: &[Permission],
) -> Result<(), String> {
    let user_perms = user_role.permissions();
    let missing: Vec<_> = required.iter()
        .filter(|p| !user_perms.contains(p))
        .collect();
    if missing.is_empty() { Ok(()) }
    else { Err(format!("Missing permissions: {:?}", missing)) }
}
```

### TypeScript

```typescript
type Permission = "read:own" | "read:all" | "write:own" | "write:all"
  | "delete:all" | "manage:users";

const ROLE_PERMISSIONS: Record<string, Set<Permission>> = {
  anonymous: new Set(),
  viewer: new Set(["read:own"]),
  editor: new Set(["read:own", "write:own"]),
  admin: new Set(["read:all", "write:all", "delete:all", "manage:users"]),
};

// Express middleware
function requirePermission(...perms: Permission[]) {
  return (req: Request, res: Response, next: NextFunction) => {
    const user = req.user;
    if (!user) return res.status(401).json({ error: "Auth required" });
    const userPerms = ROLE_PERMISSIONS[user.role] ?? new Set();
    const missing = perms.filter((p) => !userPerms.has(p));
    if (missing.length > 0) {
      return res.status(403).json({ error: `Missing: ${missing.join(", ")}` });
    }
    next();
  };
}
```

### Go

```go
package auth

import (
    "fmt"
    "net/http"
)

type Permission string

const (
    PermReadOwn     Permission = "read:own"
    PermReadAll     Permission = "read:all"
    PermWriteOwn    Permission = "write:own"
    PermWriteAll    Permission = "write:all"
    PermDeleteAll   Permission = "delete:all"
    PermManageUsers Permission = "manage:users"
)

type Role int

const (
    RoleAnonymous Role = iota
    RoleViewer
    RoleEditor
    RoleAdmin
)

func (r Role) Permissions() map[Permission]bool {
    switch r {
    case RoleViewer:
        return map[Permission]bool{PermReadOwn: true}
    case RoleEditor:
        return map[Permission]bool{PermReadOwn: true, PermWriteOwn: true}
    case RoleAdmin:
        return map[Permission]bool{
            PermReadAll: true, PermWriteAll: true,
            PermDeleteAll: true, PermManageUsers: true,
        }
    default:
        return map[Permission]bool{}
    }
}

func RequirePermission(perms ...Permission) func(http.Handler) http.Handler {
    return func(next http.Handler) http.Handler {
        return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
            user := UserFromContext(r.Context())
            if user == nil {
                http.Error(w, "auth required", http.StatusUnauthorized)
                return
            }
            userPerms := user.Role.Permissions()
            for _, p := range perms {
                if !userPerms[p] {
                    http.Error(w, fmt.Sprintf("missing: %s", p),
                        http.StatusForbidden)
                    return
                }
            }
            next.ServeHTTP(w, r)
        })
    }
}
```

### General

**Audit existing endpoints.** Walk through every route and answer:

1. Is authentication required? Any endpoint modifying data or returning non-public info needs it.
2. Is authorization checked? After authenticating, does the code verify permission for this
   specific action on this specific resource?
3. Is resource ownership validated? For `/users/{id}/data`, does the code verify the caller
   owns or has permission to access the resource identified by `{id}`?
4. Are admin functions isolated behind separate paths, additional auth (MFA), and rate limits?

**Apply least privilege:**

- Users start with zero permissions. Grant explicitly, never assume.
- Service accounts get only the permissions needed for their specific function.
- Database connections use role-specific credentials (read-only for reporting, read-write for
  app, admin-only for migrations).
- API tokens are scoped to specific operations. Elevated permissions are time-bounded.

**Test access controls explicitly:**

```python
def test_viewer_cannot_delete_resource(client, viewer_token):
    response = client.delete(
        "/api/resources/123",
        headers={"Authorization": f"Bearer {viewer_token}"},
    )
    assert response.status_code == 403, (
        f"Expected 403 for viewer DELETE, got {response.status_code}"
    )
```

## Prevention

**CI-enforceable checks:**

```yaml
access-control-audit:
  stage: lint
  script:
    - python scripts/audit_routes.py --require-auth --exclude "/health,/metrics"
    - pytest tests/unit/test_permissions.py tests/integration/test_auth.py -v
  rules:
    - if: $CI_PIPELINE_SOURCE == "merge_request_event"
      changes:
        - "src/routes/**"
        - "src/auth/**"
```

**Tools:**

- **OWASP ZAP**: Automated scanner for missing auth and broken access control.
- **semgrep**: Static analysis rules for detecting unprotected routes.

**Process:**

- Maintain a route-permission matrix listing every endpoint and its required role.
- Require security review for MRs that add or modify routes.
- Run access control tests on every MR.
- Log all access control denials with user ID, resource, and timestamp.
