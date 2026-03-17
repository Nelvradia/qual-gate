# Test Mandate Compliance Checklist

Per-skill minimum (test mandate):

- [ ] 3 unit tests per action (happy path, edge case, error case)
- [ ] CRUD functional tests with in-memory SQLite (create, read, list, filter, update, delete)
- [ ] Standard column assertions (id, tenant_id, created_at present; forward-compat columns accept NULL)
- [ ] API contract tests for exposed HTTP endpoints (status codes, auth, response shapes)
- [ ] Permission tier declaration in parametrized boundary tests
- [ ] StubLLM used for all functional tests (no real inference in CI)
- [ ] Golden path tests (accuracy targets) for cross-skill E2E chains (5 minimum)
- [ ] Regression tests present and never deleted (monotonically growing)
