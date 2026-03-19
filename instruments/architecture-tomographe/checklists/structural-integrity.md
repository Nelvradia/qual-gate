# Structural Integrity Checklist

- [ ] Module boundaries match documented architecture
- [ ] No orphan modules (every source file reachable from the module entry point — e.g. `mod.rs` in Rust, `__init__.py` in Python, `index.ts` in TypeScript)
- [ ] Public API surface is minimal (prefer internal visibility — e.g. `pub(crate)` in Rust, `_` prefix in Python, non-exported symbols in Go/TypeScript)
- [ ] Database separation matches the documented data model (schema documentation)
- [ ] Access control config domains match component/module domain registrations (when `toggles.permission_system` is true)
- [ ] Module registration in entry points matches documented module list
- [ ] No process boundary violations (independently deployed services remain separate)
- [ ] Shared types in common/core module are stable (low churn rate)
