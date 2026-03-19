---
title: "Fix: Missing Rate Limiting"
status: current
last-updated: 2026-03-19
instrument: security-tomographe
severity-range: "Major"
---

# Fix: Missing Rate Limiting

## What this means

Your API endpoints or service interfaces have no rate limiting. An attacker (or misbehaving client)
can send unlimited requests, leading to denial-of-service, brute-force credential attacks, resource
exhaustion, or inflated infrastructure costs. Rate limiting is a fundamental defence that bounds
the request rate per client, IP, or API key, ensuring fair usage and protecting backend systems
from overload. Even internal services should rate-limit to prevent cascading failures.

## How to fix

### Python

**SlowAPI for FastAPI (token bucket):**

```python
from __future__ import annotations

from fastapi import FastAPI, Request
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app = FastAPI()
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


@app.get("/api/search")
@limiter.limit("30/minute")
async def search(request: Request, q: str) -> dict:
    """Search endpoint — limited to 30 requests per minute per IP."""
    return {"query": q, "results": []}


@app.post("/api/login")
@limiter.limit("5/minute")
async def login(request: Request) -> dict:
    """Login endpoint — aggressive rate limit to prevent brute force."""
    return {"status": "ok"}
```

**django-ratelimit for Django:**

```python
from django.http import JsonResponse
from django_ratelimit.decorators import ratelimit


@ratelimit(key="ip", rate="30/m", method="GET", block=True)
def search_view(request):
    """Rate-limited search view."""
    return JsonResponse({"results": []})


@ratelimit(key="ip", rate="5/m", method="POST", block=True)
def login_view(request):
    """Aggressively rate-limited login."""
    return JsonResponse({"status": "ok"})
```

**Custom sliding window with Redis (framework-agnostic):**

```python
from __future__ import annotations

import time

import redis

_redis = redis.Redis(host="localhost", port=6379, db=0)


def is_rate_limited(key: str, max_requests: int, window_seconds: int) -> bool:
    """Check if a key has exceeded its rate limit using a sliding window.

    Args:
        key: Unique identifier (e.g., IP address, API key, user ID).
        max_requests: Maximum allowed requests in the window.
        window_seconds: Window duration in seconds.

    Returns:
        True if rate limited, False if the request should proceed.
    """
    now = time.time()
    window_start = now - window_seconds
    pipe = _redis.pipeline()
    pipe.zremrangebyscore(key, 0, window_start)  # remove expired entries
    pipe.zadd(key, {str(now): now})  # add current request
    pipe.zcard(key)  # count requests in window
    pipe.expire(key, window_seconds)  # auto-cleanup
    results = pipe.execute()
    request_count = results[2]
    return request_count > max_requests
```

### Rust

**governor crate (token bucket, production-ready):**

```rust
use governor::{Quota, RateLimiter};
use std::num::NonZeroU32;
use std::sync::Arc;

// Create a rate limiter: 30 requests per minute
fn create_limiter() -> Arc<RateLimiter<String, governor::state::keyed::DefaultKeyedStateStore<String>, governor::clock::DefaultClock>> {
    let quota = Quota::per_minute(NonZeroU32::new(30).unwrap());
    Arc::new(RateLimiter::keyed(quota))
}

// In your handler:
async fn handle_request(
    limiter: &RateLimiter<String, /* ... */>,
    client_ip: String,
) -> Result<Response, StatusCode> {
    match limiter.check_key(&client_ip) {
        Ok(_) => {
            // Request allowed — proceed
            Ok(Response::new("OK".into()))
        }
        Err(_) => {
            // Rate limited — return 429
            Err(StatusCode::TOO_MANY_REQUESTS)
        }
    }
}
```

**Tower rate limiting middleware (for axum/tonic):**

```rust
use axum::{routing::get, Router};
use tower::ServiceBuilder;
use tower::limit::RateLimitLayer;
use std::time::Duration;

fn app() -> Router {
    Router::new()
        .route("/api/search", get(search_handler))
        .layer(
            ServiceBuilder::new()
                .layer(RateLimitLayer::new(30, Duration::from_secs(60)))
        )
}
```

### TypeScript

**express-rate-limit for Express:**

```typescript
import rateLimit from "express-rate-limit";
import RedisStore from "rate-limit-redis";
import { createClient } from "redis";

const redisClient = createClient({ url: "redis://localhost:6379" });
await redisClient.connect();

// General API rate limit
const apiLimiter = rateLimit({
  windowMs: 60 * 1000, // 1 minute
  max: 30, // 30 requests per window per IP
  standardHeaders: true, // Return rate limit info in RateLimit-* headers
  legacyHeaders: false,
  store: new RedisStore({
    sendCommand: (...args: string[]) => redisClient.sendCommand(args),
  }),
  message: { error: "Too many requests, please try again later." },
});

// Strict limit for auth endpoints
const authLimiter = rateLimit({
  windowMs: 60 * 1000,
  max: 5,
  standardHeaders: true,
  legacyHeaders: false,
  skipSuccessfulRequests: false,
});

app.use("/api/", apiLimiter);
app.use("/api/login", authLimiter);
app.use("/api/register", authLimiter);
```

**@nestjs/throttler for NestJS:**

```typescript
import { ThrottlerModule, ThrottlerGuard } from "@nestjs/throttler";
import { APP_GUARD } from "@nestjs/core";

@Module({
  imports: [
    ThrottlerModule.forRoot([
      {
        name: "short",
        ttl: 1000,  // 1 second
        limit: 3,   // 3 requests per second
      },
      {
        name: "medium",
        ttl: 60000, // 1 minute
        limit: 30,  // 30 requests per minute
      },
    ]),
  ],
  providers: [
    {
      provide: APP_GUARD,
      useClass: ThrottlerGuard,
    },
  ],
})
export class AppModule {}

// Override per-route
@Controller("auth")
export class AuthController {
  @Throttle({ short: { ttl: 60000, limit: 5 } })
  @Post("login")
  async login() {
    // 5 attempts per minute
  }
}
```

### Go

**golang.org/x/time/rate (stdlib-adjacent, token bucket):**

```go
package main

import (
    "net/http"
    "sync"

    "golang.org/x/time/rate"
)

type IPRateLimiter struct {
    mu       sync.RWMutex
    limiters map[string]*rate.Limiter
    rate     rate.Limit
    burst    int
}

func NewIPRateLimiter(r rate.Limit, burst int) *IPRateLimiter {
    return &IPRateLimiter{
        limiters: make(map[string]*rate.Limiter),
        rate:     r,
        burst:    burst,
    }
}

func (rl *IPRateLimiter) GetLimiter(ip string) *rate.Limiter {
    rl.mu.Lock()
    defer rl.mu.Unlock()

    limiter, exists := rl.limiters[ip]
    if !exists {
        limiter = rate.NewLimiter(rl.rate, rl.burst)
        rl.limiters[ip] = limiter
    }
    return limiter
}

// Middleware
func rateLimitMiddleware(rl *IPRateLimiter) func(http.Handler) http.Handler {
    return func(next http.Handler) http.Handler {
        return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
            limiter := rl.GetLimiter(r.RemoteAddr)
            if !limiter.Allow() {
                w.Header().Set("Retry-After", "60")
                http.Error(w, "Too many requests", http.StatusTooManyRequests)
                return
            }
            next.ServeHTTP(w, r)
        })
    }
}

// Usage: 30 requests per minute with burst of 5
// limiter := NewIPRateLimiter(rate.Every(2*time.Second), 5)
// mux.Handle("/api/", rateLimitMiddleware(limiter)(apiHandler))
```

**tollbooth for simpler setup:**

```go
import "github.com/didip/tollbooth/v8"

func main() {
    // 30 requests per minute
    lmt := tollbooth.NewLimiter(0.5, nil) // 0.5 req/sec = 30/min
    lmt.SetIPLookups([]string{"X-Forwarded-For", "X-Real-IP", "RemoteAddr"})
    lmt.SetMessage("Rate limit exceeded. Try again later.")

    mux := http.NewServeMux()
    mux.Handle("/api/search", tollbooth.LimitFuncHandler(lmt, searchHandler))
    http.ListenAndServe(":8080", mux)
}
```

### General

**Rate limiting strategies:**

| Algorithm       | Behaviour                                   | Best for                        |
|----------------|---------------------------------------------|---------------------------------|
| Token bucket   | Allows bursts up to bucket size, refills     | APIs with bursty legitimate use |
| Sliding window | Counts requests in a rolling time window     | Even distribution enforcement   |
| Fixed window   | Counts requests in fixed time slots          | Simple, but allows burst at edges|
| Leaky bucket   | Processes requests at a fixed rate           | Queue-based processing          |

**What to rate limit and recommended limits:**

| Endpoint type            | Suggested limit       | Rationale                        |
|-------------------------|-----------------------|----------------------------------|
| Login / auth            | 5–10/min per IP       | Brute-force prevention           |
| Password reset          | 3/hour per account    | Prevent account enumeration      |
| API search / list       | 30–60/min per key     | Prevent scraping                 |
| File upload             | 10/hour per user      | Prevent storage abuse            |
| Webhook receivers       | 100/min per source    | Prevent amplification attacks    |
| Health check            | No limit (or very high)| Must remain available            |

**Response headers (RFC 6585 / draft-ietf-httpapi-ratelimit-headers):**

```
HTTP/1.1 429 Too Many Requests
Retry-After: 60
RateLimit-Limit: 30
RateLimit-Remaining: 0
RateLimit-Reset: 1679529600
```

Always return `Retry-After` with 429 responses so clients can back off appropriately.

**API gateway rate limiting:**

For production deployments, implement rate limiting at the gateway layer (nginx, Kong, Envoy,
AWS API Gateway) in addition to application-level limits. Gateway limits protect against
volumetric attacks before they reach your application:

```nginx
# nginx rate limiting
limit_req_zone $binary_remote_addr zone=api:10m rate=30r/m;

server {
    location /api/ {
        limit_req zone=api burst=10 nodelay;
        limit_req_status 429;
        proxy_pass http://backend;
    }
}
```

## Prevention

- **Load testing in CI:** Run `k6` or `locust` against staging with rate limits enabled.
  Verify that 429s are returned when limits are exceeded.
- **Monitoring and alerting:** Track 429 response rates. A spike in 429s may indicate an
  attack or a misconfigured client. Alert on sustained high 429 rates.
- **Per-tenant configuration:** Make rate limits configurable per API key or tenant tier.
  Store limits in a database or config file, not hardcoded.
- **Distributed rate limiting:** For multi-instance deployments, use a shared store (Redis,
  Memcached) for rate limit counters. In-memory limiters only work for single-instance
  deployments.
- **Circuit breaker pattern:** Combine rate limiting with circuit breakers. If a downstream
  service is overloaded, stop sending requests entirely rather than rate-limiting trickle.
- **Documentation:** Document rate limits in your API docs. Clients need to know limits to
  implement proper backoff and retry logic.
