# Security Posture Checklist

Master checklist covering all security domains. Used by Phase 8 (Report) to compute overall security score.

## Authentication & Access Control
- [ ] Bearer token auth enforced on all endpoints (except /health)
- [ ] Token has expiry and rotation mechanism
- [ ] Device pairing uses X3DH key exchange
- [ ] Biometric gate for T3+ actions (Android)
- [ ] Permission service fail-closed (unreachable → all blocked)
- [ ] All actions declared in permission/access control configuration
- [ ] T0 hard-locks on financial + communication + destructive actions

## Secrets Management
- [ ] No credentials in source code
- [ ] No credentials in git history
- [ ] .env files gitignored
- [ ] .env.example uses placeholder values only
- [ ] Secrets scanning in CI pipeline (gitleaks)

## Encryption
- [ ] Confidential/Restricted databases encrypted (SQLCipher)
- [ ] E2E encryption mandatory (no unencrypted fallback)
- [ ] TLS on all network connections
- [ ] Keys in hardware-backed storage (Android Keystore / OS keyring)

## Container Security
- [ ] Permission service + monitoring service containers read-only
- [ ] No privileged containers
- [ ] Docker socket not mounted in production
- [ ] Resource limits set
- [ ] Non-root users in Dockerfiles
- [ ] Images pinned to digest (not tag)

## AI-Specific Security
- [ ] Input sanitization on all external content
- [ ] Content isolation between RAG scopes
- [ ] Output validation (Layer 4 defense)
- [ ] Adversarial test dataset exists (≥50 patterns)
- [ ] System prompt not leakable

## Supply Chain
- [ ] cargo audit clean (0 critical/high)
- [ ] pip audit clean
- [ ] npm audit clean
- [ ] Docker images scanned (trivy)
- [ ] Dependencies pinned (Cargo.lock committed)
