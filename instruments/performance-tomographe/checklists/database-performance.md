# Database Performance Checklist

SQLite-specific optimizations for the project's databases.

## Configuration
- [ ] WAL mode enabled (`PRAGMA journal_mode=WAL`)
- [ ] Synchronous mode NORMAL (`PRAGMA synchronous=NORMAL`)
- [ ] Busy timeout configured (`PRAGMA busy_timeout=5000`)
- [ ] Cache size adequate (`PRAGMA cache_size=-64000` for 64MB)
- [ ] Memory-mapped I/O enabled (`PRAGMA mmap_size=268435456`)

## Indexes
- [ ] All foreign key columns indexed (`*_id`)
- [ ] Frequently filtered columns indexed (created_at, status, domain, tenant_id)
- [ ] No redundant indexes (same columns covered by different indexes)
- [ ] Composite indexes for multi-column WHERE clauses

## Query Patterns
- [ ] No full table scans in request hot path
- [ ] No N+1 queries (loop containing queries)
- [ ] LIMIT used on all list queries
- [ ] COUNT uses index where possible
- [ ] No LIKE '%pattern%' on large tables without FTS

## Connection Management
- [ ] Connection pooling or persistent connection (not open-per-query)
- [ ] Connections closed on error (no leaking)
- [ ] WAL checkpoint scheduled (not only on close)
