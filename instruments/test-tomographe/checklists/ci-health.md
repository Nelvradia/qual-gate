# CI Health Checklist

- [ ] All unit tests are merge-blocking (not allow_failure)
- [ ] All functional tests are merge-blocking
- [ ] All migration tests are merge-blocking
- [ ] All regression tests are merge-blocking (zero tolerance)
- [ ] Permission boundary tests are merge-blocking
- [ ] cargo fmt --check is merge-blocking
- [ ] No allow_failure jobs without a tracking issue
- [ ] Full test suite completes in <180 seconds
- [ ] No known flaky tests (tests that fail intermittently)
- [ ] Golden path tests pass on main branch
- [ ] CI pipeline defined for all repos (core, desktop, android)
