# Structural Integrity Checklist

- [ ] Crate boundaries match documented architecture in CLAUDE.md
- [ ] No orphan modules (every .rs file reachable from mod.rs/main.rs)
- [ ] Public API surface is minimal (prefer pub(crate) over pub)
- [ ] Database separation matches the database model (schema documentation)
- [ ] Permission config domains match component/module domain registrations
- [ ] Skill registration in mod.rs matches documented skill list
- [ ] No process boundary violations (core service, permission service, monitoring service are separate)
- [ ] Shared types in common crate are stable (low churn rate)
