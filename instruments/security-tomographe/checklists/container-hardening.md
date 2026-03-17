# Container Hardening Checklist

Per CIS Docker Benchmark.

- [ ] No container runs as root (USER directive in Dockerfile)
- [ ] read_only: true on permission service and monitoring service
- [ ] tmpfs for /tmp where needed
- [ ] No privileged mode
- [ ] No Docker socket mounting in production
- [ ] Resource limits (memory, CPU) set
- [ ] Health checks defined for all services
- [ ] Internal-only Docker network for inter-service communication
- [ ] No unnecessary ports exposed to host
- [ ] Secrets via env vars or Docker secrets (not baked into image)
- [ ] Image digests pinned (not mutable tags)
- [ ] Multi-stage builds (no build tools in production image)
