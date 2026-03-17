# Pattern Fitness Checklist

- [ ] Service follows api → skill → db layer boundary
- [ ] No circular dependencies between workspace crates
- [ ] Skills do not import other skills directly
- [ ] Permission service operates independently (no core service/monitoring service imports)
- [ ] Monitoring service operates independently (no core service/permission service imports)
- [ ] Raw SQL confined to db/ layer (not in skill/ or api/)
- [ ] HTTP types confined to api/ layer (not in db/ or skill/)
- [ ] Permission service behavior is config-driven (not hardcoded)
- [ ] Common crate contains only shared types (no business logic)
- [ ] No permission bypass paths exist in service code
