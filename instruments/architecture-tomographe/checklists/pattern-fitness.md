# Pattern Fitness Checklist

## Universal Checks (always apply)

- [ ] No circular dependencies between modules/crates/packages
- [ ] Raw data access confined to designated persistence layer (not in API or business logic)
- [ ] HTTP/transport types confined to API layer (not in persistence or business logic)
- [ ] Common/shared module contains only shared types (no business logic)
- [ ] No auth/permission bypass paths in service code

## Profile-Driven Checks (generated from project-profile.yaml)

These checks are generated at scan time based on the target project's profile.
Skip this section entirely if the relevant profile fields are absent.

### Layer Boundary (requires `architecture.layers`)
- [ ] Service follows declared layer boundary order (e.g. api → service → db)
- [ ] No upward dependencies between layers

### Component Independence (requires `architecture.entry_points` with multiple services)
- [ ] Declared independent services do not import each other's internal modules

### Permission System (requires `toggles.permission_system: true`)
- [ ] Permission/access control service operates independently (no core service imports)
- [ ] Permission service behaviour is config-driven (not hardcoded)
