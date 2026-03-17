# CI Pipeline Checklist
- [ ] All stages present (validate, test, build, integration, release, deploy)
- [ ] cargo fmt is merge-blocking
- [ ] cargo clippy is merge-blocking
- [ ] cargo test is merge-blocking
- [ ] Integration tests run on merge to main
- [ ] DR gate validates report on tags
- [ ] No critical job has allow_failure: true
- [ ] Timeouts configured on all jobs
