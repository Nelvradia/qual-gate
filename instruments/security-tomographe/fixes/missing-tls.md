---
title: "Fix: Missing TLS"
status: current
last-updated: 2026-03-19
instrument: security-tomographe
severity-range: "Critical–Major"
---

# Fix: Missing TLS

## What this means

Your application serves traffic or makes outbound connections over plaintext HTTP, WS, or
unencrypted TCP. This allows any network observer — on the local network, at an ISP, or on
public Wi-Fi — to read and modify data in transit. Credentials, session tokens, PII, and API
payloads are all exposed. Man-in-the-middle (MitM) attacks become trivial: an attacker can
intercept requests, inject malicious responses, or steal authentication tokens without the
client or server detecting tampering. All production traffic must use TLS 1.2 or later.

## How to fix

### Python

**Uvicorn with TLS (FastAPI / Starlette):**

```python
# Run uvicorn with SSL certificates
# uvicorn main:app --host 0.0.0.0 --port 443 \
#   --ssl-keyfile /etc/certs/key.pem \
#   --ssl-certfile /etc/certs/cert.pem

# In code — redirect HTTP to HTTPS
from fastapi import FastAPI
from starlette.middleware.httpsredirect import HTTPSRedirectMiddleware

app = FastAPI()
app.add_middleware(HTTPSRedirectMiddleware)
```

**Enforce TLS on outbound requests:**

```python
import requests

# verify=True is the default — never set verify=False in production
response = requests.get("https://api.example.com/data", verify=True)

# Pin a specific CA bundle if needed
response = requests.get(
    "https://internal.example.com/data",
    verify="/etc/ssl/certs/internal-ca.pem",
)

# BAD — never do this in production
# response = requests.get("https://...", verify=False)  # disables TLS verification
```

**Django HTTPS settings:**

```python
# settings.py
SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 31536000        # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
```

**Certificate management with certbot:**

```bash
# Obtain a Let's Encrypt certificate
certbot certonly --standalone -d api.example.com

# Auto-renewal (add to cron or systemd timer)
certbot renew --quiet
```

### Rust

**Axum with rustls:**

```rust
// Cargo.toml
// [dependencies]
// axum = "0.8"
// axum-server = { version = "0.7", features = ["tls-rustls"] }
// tokio = { version = "1", features = ["full"] }

use axum::{routing::get, Router};
use axum_server::tls_rustls::RustlsConfig;
use std::net::SocketAddr;

#[tokio::main]
async fn main() {
    let tls_config = RustlsConfig::from_pem_file(
        "/etc/certs/cert.pem",
        "/etc/certs/key.pem",
    )
    .await
    .expect("Failed to load TLS certificates");

    let app = Router::new().route("/", get(|| async { "Hello, TLS!" }));

    let addr = SocketAddr::from(([0, 0, 0, 0], 443));
    axum_server::bind_rustls(addr, tls_config)
        .serve(app.into_make_service())
        .await
        .expect("Server failed to start");
}
```

**Enforce TLS on outbound requests with reqwest:**

```rust
use reqwest::Client;

// Default client verifies TLS — do not call danger_accept_invalid_certs()
let client = Client::new();
let response = client.get("https://api.example.com/data")
    .send()
    .await?;
```

### TypeScript

**Node.js HTTPS server:**

```typescript
import * as https from "https";
import * as fs from "fs";
import express from "express";

const app = express();

const options = {
  key: fs.readFileSync("/etc/certs/key.pem"),
  cert: fs.readFileSync("/etc/certs/cert.pem"),
  minVersion: "TLSv1.2" as const,
};

https.createServer(options, app).listen(443, () => {
  console.log("HTTPS server running on port 443");
});
```

**HSTS with helmet:**

```typescript
import helmet from "helmet";

app.use(
  helmet.hsts({
    maxAge: 31536000,        // 1 year in seconds
    includeSubDomains: true,
    preload: true,
  })
);
```

**Redirect HTTP to HTTPS (Express middleware):**

```typescript
app.use((req, res, next) => {
  if (req.header("x-forwarded-proto") !== "https") {
    return res.redirect(301, `https://${req.hostname}${req.url}`);
  }
  next();
});
```

**WebSocket over TLS:** Create an `https.createServer` with your cert/key, then pass it to
`new WebSocketServer({ server })`. All WebSocket connections will use WSS automatically.

### Go

**Standard library TLS server:**

```go
package main

import (
    "crypto/tls"
    "log"
    "net/http"
)

func main() {
    mux := http.NewServeMux()
    mux.HandleFunc("/", func(w http.ResponseWriter, r *http.Request) {
        w.Write([]byte("Hello, TLS!"))
    })

    tlsConfig := &tls.Config{
        MinVersion: tls.VersionTLS12,
    }

    server := &http.Server{
        Addr:      ":443",
        Handler:   mux,
        TLSConfig: tlsConfig,
    }

    log.Fatal(server.ListenAndServeTLS("/etc/certs/cert.pem", "/etc/certs/key.pem"))
}
```

**Automatic certificates:** Use `golang.org/x/crypto/acme/autocert` with an `autocert.Manager`
to obtain and renew Let's Encrypt certificates automatically. Set `HostPolicy` to allowlist
your domains.

### General

**Reverse proxy TLS termination (recommended for most setups):**

Rather than managing TLS in every application, terminate TLS at a reverse proxy and forward
plaintext traffic to the application over a trusted internal network or Unix socket.

**Nginx example:**

```nginx
server {
    listen 443 ssl http2;
    server_name api.example.com;

    ssl_certificate     /etc/letsencrypt/live/api.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.example.com/privkey.pem;
    ssl_protocols       TLSv1.2 TLSv1.3;
    ssl_prefer_server_ciphers on;

    # HSTS header
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload";

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}

# Redirect HTTP to HTTPS
server {
    listen 80;
    server_name api.example.com;
    return 301 https://$server_name$request_uri;
}
```

**HSTS rollout:**

- Start with a short `max-age` (e.g., 300 seconds) to verify HTTPS works everywhere.
- Increase to 1 year (31536000) once confirmed.
- Add `includeSubDomains` only after verifying all subdomains support HTTPS.
- Submit to the [HSTS preload list](https://hstspreload.org/) for browser-level enforcement.

**Kubernetes:** Use [cert-manager](https://cert-manager.io/) with a `ClusterIssuer` and
`Ingress` annotation to automate Let's Encrypt certificates per-service.

## Prevention

**CI checks:**

```yaml
# Scan for http:// URLs in source code (excluding test fixtures and docs)
plaintext-url-scan:
  stage: lint
  script:
    - |
      if grep -rn "http://" src/ --include="*.py" --include="*.rs" \
           --include="*.ts" --include="*.go" \
           | grep -v "http://localhost" \
           | grep -v "http://127.0.0.1" \
           | grep -v "http://0.0.0.0"; then
        echo "ERROR: Found hardcoded http:// URLs. Use https:// instead."
        exit 1
      fi
```

**Ongoing monitoring:**

- Monitor certificate expiry — alert at 30 days. Automate renewal with certbot or cert-manager.
- Test TLS configuration with [SSL Labs](https://www.ssllabs.com/ssltest/) — aim for A+ grade.
- Validate security headers with [Mozilla Observatory](https://observatory.mozilla.org/).
- Disable TLS 1.0/1.1 and weak cipher suites (RC4, 3DES, export ciphers).
