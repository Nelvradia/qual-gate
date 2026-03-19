---
title: "Fix: Insecure Key Storage"
status: current
last-updated: 2026-03-19
instrument: security-tomographe
severity-range: "Major–Critical"
---

# Fix: Insecure Key Storage

## What this means

Cryptographic keys, API tokens, or other secrets are stored insecurely — in plaintext files, source
code, environment variables accessible to all processes, or in databases without encryption at rest.
If an attacker gains read access to the filesystem, database, or process environment, they obtain
the keys and can impersonate users, decrypt data, or access external services. Proper key storage
uses platform-native secure enclaves, hardware security modules, or dedicated secret management
systems that limit key exposure to the specific process that needs it.

## How to fix

### Python

**keyring library — OS-native credential storage:**

```python
from __future__ import annotations

import keyring

# Store a secret in the OS keyring (GNOME Keyring, macOS Keychain, Windows Credential Locker)
keyring.set_password("myapp", "api_token", "sk-secret-value-here")

# Retrieve it at runtime
token = keyring.get_password("myapp", "api_token")
if token is None:
    raise RuntimeError("API token not found in keyring — run setup first")
```

**cryptography.fernet for encrypting secrets at rest:**

```python
from __future__ import annotations

from cryptography.fernet import Fernet


def encrypt_secret(plaintext: str, key: bytes) -> bytes:
    """Encrypt a secret using Fernet symmetric encryption.

    Args:
        plaintext: The secret value to encrypt.
        key: A 32-byte URL-safe base64-encoded key (from Fernet.generate_key()).

    Returns:
        The encrypted token as bytes.
    """
    f = Fernet(key)
    return f.encrypt(plaintext.encode("utf-8"))


def decrypt_secret(token: bytes, key: bytes) -> str:
    """Decrypt a Fernet-encrypted secret."""
    f = Fernet(key)
    return f.decrypt(token).decode("utf-8")


# Key generation (do this once, store the key in a secure location)
# master_key = Fernet.generate_key()
```

**HashiCorp Vault integration:**

```python
from __future__ import annotations

import hvac


def get_secret_from_vault(path: str, key: str) -> str:
    """Retrieve a secret from HashiCorp Vault.

    Args:
        path: The Vault secret path (e.g., 'secret/data/myapp/db').
        key: The key within the secret data.

    Returns:
        The secret value.
    """
    client = hvac.Client(
        url="https://vault.internal:8200",
        token=None,  # Use AppRole or Kubernetes auth, never hardcode tokens
    )
    # Authenticate via AppRole
    client.auth.approle.login(
        role_id=os.environ["VAULT_ROLE_ID"],
        secret_id=os.environ["VAULT_SECRET_ID"],
    )
    response = client.secrets.kv.v2.read_secret_version(path=path)
    return response["data"]["data"][key]
```

### Rust

**keyring crate — cross-platform credential storage:**

```rust
use keyring::Entry;

fn store_api_key(service: &str, user: &str, key: &str) -> Result<(), keyring::Error> {
    let entry = Entry::new(service, user)?;
    entry.set_password(key)?;
    Ok(())
}

fn get_api_key(service: &str, user: &str) -> Result<String, keyring::Error> {
    let entry = Entry::new(service, user)?;
    entry.get_password()
}

// Usage:
// store_api_key("myapp", "api_token", "sk-secret-value")?;
// let token = get_api_key("myapp", "api_token")?;
```

**Encrypting secrets with ring (for at-rest encryption):**

```rust
use ring::aead::{self, Aad, LessSafeKey, Nonce, UnboundKey, CHACHA20_POLY1305};
use ring::rand::{SecureRandom, SystemRandom};

fn encrypt(key_bytes: &[u8; 32], plaintext: &[u8]) -> Result<Vec<u8>, ring::error::Unspecified> {
    let unbound_key = UnboundKey::new(&CHACHA20_POLY1305, key_bytes)?;
    let key = LessSafeKey::new(unbound_key);
    let rng = SystemRandom::new();

    let mut nonce_bytes = [0u8; 12];
    rng.fill(&mut nonce_bytes)?;
    let nonce = Nonce::assume_unique_for_key(nonce_bytes);

    let mut in_out = plaintext.to_vec();
    key.seal_in_place_append_tag(nonce, Aad::empty(), &mut in_out)?;

    // Prepend nonce to ciphertext for storage
    let mut result = nonce_bytes.to_vec();
    result.extend_from_slice(&in_out);
    Ok(result)
}
```

### TypeScript

**Web Crypto API (browser — key generation and wrapping):**

```typescript
async function generateAndWrapKey(): Promise<{
  wrappedKey: ArrayBuffer;
  wrappingKey: CryptoKey;
}> {
  // Generate a wrapping key (store this in a secure location)
  const wrappingKey = await crypto.subtle.generateKey(
    { name: "AES-GCM", length: 256 },
    true, // extractable for export
    ["wrapKey", "unwrapKey"]
  );

  // Generate the actual secret key
  const secretKey = await crypto.subtle.generateKey(
    { name: "AES-GCM", length: 256 },
    true,
    ["encrypt", "decrypt"]
  );

  // Wrap (encrypt) the secret key with the wrapping key
  const iv = crypto.getRandomValues(new Uint8Array(12));
  const wrappedKey = await crypto.subtle.wrapKey("raw", secretKey, wrappingKey, {
    name: "AES-GCM",
    iv,
  });

  return { wrappedKey, wrappingKey };
}
```

**Secure cookies for server-side token storage (Express):**

```typescript
import session from "express-session";

app.use(
  session({
    secret: process.env.SESSION_SECRET!, // loaded from vault, not hardcoded
    name: "__Host-sid", // __Host- prefix enforces Secure + path=/
    cookie: {
      httpOnly: true, // not accessible via JavaScript
      secure: true, // HTTPS only
      sameSite: "strict", // CSRF protection
      maxAge: 3600_000, // 1 hour
    },
    resave: false,
    saveUninitialized: false,
  })
);
```

**Node.js server — avoid storing keys in env vars visible to child processes:**

```typescript
import { readFileSync } from "fs";

// Load key from a mounted secret file (Docker secret, K8s secret volume)
function loadKey(path: string): string {
  const key = readFileSync(path, "utf-8").trim();
  if (key.length === 0) {
    throw new Error(`Secret file is empty: ${path}`);
  }
  return key;
}

// Docker: mount as /run/secrets/api_key
// K8s: mount as /etc/secrets/api_key
const apiKey = loadKey("/run/secrets/api_key");
```

### Go

**go-keyring for desktop applications:**

```go
package main

import "github.com/zalando/go-keyring"

func storeSecret(service, user, secret string) error {
    return go_keyring.Set(service, user, secret)
}

func getSecret(service, user string) (string, error) {
    return go_keyring.Get(service, user)
}
```

**Reading secrets from mounted files (containers):**

```go
func loadSecret(path string) (string, error) {
    data, err := os.ReadFile(path)
    if err != nil {
        return "", fmt.Errorf("reading secret from %s: %w", path, err)
    }
    secret := strings.TrimSpace(string(data))
    if secret == "" {
        return "", fmt.Errorf("secret file is empty: %s", path)
    }
    return secret, nil
}
```

**HashiCorp Vault integration:**

```go
import vault "github.com/hashicorp/vault/api"

func getVaultSecret(path, key string) (string, error) {
    config := vault.DefaultConfig()
    client, err := vault.NewClient(config)
    if err != nil {
        return "", fmt.Errorf("creating vault client: %w", err)
    }

    secret, err := client.KVv2("secret").Get(context.Background(), path)
    if err != nil {
        return "", fmt.Errorf("reading secret %s: %w", path, err)
    }

    value, ok := secret.Data[key].(string)
    if !ok {
        return "", fmt.Errorf("key %s not found or not a string in %s", key, path)
    }
    return value, nil
}
```

### General

**Platform-specific secure storage:**

| Platform     | Mechanism                          | Notes                                      |
|-------------|------------------------------------|--------------------------------------------|
| Linux       | GNOME Keyring / KDE Wallet / libsecret | D-Bus-based, per-user, encrypted at rest |
| macOS       | Keychain Services                  | Hardware-backed on Apple Silicon            |
| Windows     | Credential Locker / DPAPI         | Per-user, tied to Windows login credentials |
| Android     | Android Keystore                   | Hardware-backed (TEE/Strongbox)            |
| iOS         | Keychain Services                  | Secure Enclave integration                  |
| Web browser | Web Crypto API + IndexedDB         | Non-extractable keys via CryptoKey          |
| Containers  | Mounted secrets (Docker/K8s)       | tmpfs-backed, never in image layers        |

**Key management best practices:**

1. **Never store keys in source code, config files, or environment variables.** Use secret
   management systems (Vault, AWS Secrets Manager, Azure Key Vault, GCP Secret Manager).
2. **Rotate keys regularly.** Define a rotation schedule — 90 days for API keys, annually for
   encryption keys. Automate rotation where possible.
3. **Use envelope encryption.** Encrypt data keys with a master key. Rotate data keys without
   re-encrypting all data. Only the master key needs HSM-level protection.
4. **Audit key access.** Log every key retrieval with timestamp, requester identity, and purpose.
   Alert on anomalous access patterns.
5. **Separate keys by environment.** Production keys must never appear in development or staging.
   Use distinct key hierarchies per environment.

**Docker and Kubernetes secrets:**

```yaml
# docker-compose.yml — use Docker secrets
services:
  app:
    secrets:
      - api_key
      - db_password
secrets:
  api_key:
    file: ./secrets/api_key.txt  # not checked into git
  db_password:
    external: true  # managed outside compose
```

```yaml
# Kubernetes — mount secrets as files, not env vars
apiVersion: v1
kind: Pod
spec:
  containers:
    - name: app
      volumeMounts:
        - name: secrets
          mountPath: /etc/secrets
          readOnly: true
  volumes:
    - name: secrets
      secret:
        secretName: app-secrets
```

## Prevention

- **Secret scanning in CI:** Use `trufflehog`, `gitleaks`, or `detect-secrets` to catch keys
  committed to source control. Run on every push and as a pre-commit hook.
- **Pre-commit hook:** `detect-secrets` as a pre-commit hook prevents secrets from being
  committed in the first place.
- **GitLab secret detection:** Enable the built-in secret detection CI template if available.
- **Key rotation alerts:** Set up monitoring that alerts when keys exceed their rotation age.
- **Least privilege:** Grant each service only the specific keys it needs. Never share a single
  key across multiple services or environments.
- **Secrets audit:** Quarterly review of all stored secrets — remove unused keys, verify rotation
  compliance, check access logs for anomalies.
