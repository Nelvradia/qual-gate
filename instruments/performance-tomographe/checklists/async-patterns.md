# Async Pattern Checklist

Detect blocking operations in async context — the #1 performance killer in Tokio apps.

## Critical (blocks the entire Tokio runtime thread)
- [ ] No `std::thread::sleep` in async functions (use `tokio::time::sleep`)
- [ ] No `std::fs::read/write` in async functions (use `tokio::fs`)
- [ ] No `std::sync::Mutex` held across `.await` points (use `tokio::sync::Mutex`)
- [ ] No blocking DNS resolution in async context

## Important
- [ ] No `reqwest::blocking` in async code
- [ ] Database queries use async driver or spawn_blocking
- [ ] File I/O wrapped in `tokio::task::spawn_blocking` if sync-only
- [ ] CPU-heavy computation offloaded to `spawn_blocking`

## Optimization
- [ ] Connection pooling for database and HTTP clients
- [ ] Avoid unnecessary `.clone()` in request handlers
- [ ] Buffer sizes appropriate (not too large for small messages)
- [ ] Timeouts set on all external calls (LLM, vector database, HTTP)
