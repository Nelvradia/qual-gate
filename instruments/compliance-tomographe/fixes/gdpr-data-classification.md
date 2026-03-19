---
title: "Fix: GDPR Data Classification"
status: current
last-updated: 2026-03-19
instrument: compliance-tomographe
severity-range: "Major–Critical"
---

# Fix: GDPR Data Classification

## What this means

Your project processes personal data without a clear classification scheme, data flow map, or
retention policy. Under the EU General Data Protection Regulation (GDPR), any system that
collects, stores, transmits, or processes personal data must document what data it holds, why,
for how long, and who can access it. Missing classification means you cannot demonstrate
compliance to regulators, cannot respond accurately to data subject access requests (DSARs),
and risk unlawful processing of sensitive categories (health, biometric, racial/ethnic data)
without appropriate safeguards.

## How to fix

### Step 1: Classify data into privacy tiers

Define tiers that map to GDPR categories and drive technical controls:

| Tier | Description | Examples | Controls |
|---|---|---|---|
| **T0 -- Public** | Non-personal, publicly available | Product names, docs | No restrictions |
| **T1 -- Internal** | Non-personal, business-internal | System metrics, logs | Access control |
| **T2 -- Personal** | Identifies a natural person | Name, email, user ID | Encryption, RBAC, audit |
| **T3 -- Sensitive** | GDPR Art. 9 special categories | Health, biometrics, ethnicity | Explicit consent, DPO review |
| **T4 -- Restricted** | High-risk personal data | Financial, government ID, location history | Encryption at rest + transit, MFA, DPO sign-off |

### Python

```python
from __future__ import annotations

from enum import Enum
from dataclasses import dataclass


class PrivacyTier(Enum):
    """GDPR-aligned data classification tiers."""

    PUBLIC = 0
    INTERNAL = 1
    PERSONAL = 2
    SENSITIVE = 3
    RESTRICTED = 4


@dataclass(frozen=True)
class FieldClassification:
    """Classification metadata for a data field."""

    field_name: str
    tier: PrivacyTier
    purpose: str  # Why this data is collected (GDPR Art. 5(1)(b))
    retention_days: int | None  # None = kept until deletion request
    legal_basis: str  # consent, contract, legitimate_interest, legal_obligation


# Example: classify a user profile schema
USER_PROFILE_FIELDS = [
    FieldClassification("user_id", PrivacyTier.PERSONAL, "account identification",
                        None, "contract"),
    FieldClassification("email", PrivacyTier.PERSONAL, "account communication",
                        None, "contract"),
    FieldClassification("full_name", PrivacyTier.PERSONAL, "personalisation",
                        None, "contract"),
    FieldClassification("date_of_birth", PrivacyTier.RESTRICTED, "age verification",
                        365 * 3, "legal_obligation"),
    FieldClassification("ip_address", PrivacyTier.PERSONAL, "security audit",
                        90, "legitimate_interest"),
    FieldClassification("health_status", PrivacyTier.SENSITIVE, "accessibility",
                        30, "consent"),
]
```

### Rust

```rust
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum PrivacyTier {
    Public,
    Internal,
    Personal,
    Sensitive,
    Restricted,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FieldClassification {
    pub field_name: String,
    pub tier: PrivacyTier,
    pub purpose: String,
    pub retention_days: Option<u32>,
    pub legal_basis: String,
}

/// Validate that sensitive fields have explicit consent as legal basis.
pub fn validate_classifications(
    fields: &[FieldClassification],
) -> Vec<String> {
    let mut violations = Vec::new();
    for field in fields {
        if field.tier == PrivacyTier::Sensitive
            && field.legal_basis != "consent"
        {
            violations.push(format!(
                "Field '{}' is Sensitive but legal basis is '{}', expected 'consent'",
                field.field_name, field.legal_basis
            ));
        }
        if field.tier as u8 >= PrivacyTier::Personal as u8
            && field.retention_days.is_none()
        {
            violations.push(format!(
                "Field '{}' (tier {:?}) has no retention period defined",
                field.field_name, field.tier
            ));
        }
    }
    violations
}
```

### TypeScript

```typescript
enum PrivacyTier {
  PUBLIC = 0,
  INTERNAL = 1,
  PERSONAL = 2,
  SENSITIVE = 3,
  RESTRICTED = 4,
}

interface FieldClassification {
  fieldName: string;
  tier: PrivacyTier;
  purpose: string;
  retentionDays: number | null;
  legalBasis:
    | "consent"
    | "contract"
    | "legitimate_interest"
    | "legal_obligation";
}

function validateClassifications(
  fields: FieldClassification[]
): string[] {
  const violations: string[] = [];
  for (const field of fields) {
    if (
      field.tier === PrivacyTier.SENSITIVE &&
      field.legalBasis !== "consent"
    ) {
      violations.push(
        `Field '${field.fieldName}' is Sensitive but uses '${field.legalBasis}', ` +
        `requires 'consent'`
      );
    }
  }
  return violations;
}
```

### Go

```go
package privacy

// PrivacyTier represents GDPR-aligned data classification.
type PrivacyTier int

const (
    TierPublic     PrivacyTier = iota
    TierInternal
    TierPersonal
    TierSensitive
    TierRestricted
)

// FieldClassification holds classification metadata for a data field.
type FieldClassification struct {
    FieldName     string      `json:"field_name"`
    Tier          PrivacyTier `json:"tier"`
    Purpose       string      `json:"purpose"`
    RetentionDays *int        `json:"retention_days"` // nil = until deletion
    LegalBasis    string      `json:"legal_basis"`
}

// ValidateClassifications checks that field classifications follow GDPR rules.
func ValidateClassifications(fields []FieldClassification) []string {
    var violations []string
    for _, f := range fields {
        if f.Tier == TierSensitive && f.LegalBasis != "consent" {
            violations = append(violations, fmt.Sprintf(
                "field '%s' is Sensitive but legal basis is '%s'",
                f.FieldName, f.LegalBasis,
            ))
        }
        if f.Tier >= TierPersonal && f.RetentionDays == nil {
            violations = append(violations, fmt.Sprintf(
                "field '%s' (tier %d) has no retention period",
                f.FieldName, f.Tier,
            ))
        }
    }
    return violations
}
```

### General

### Step 2: Map data flows

Document where personal data enters, moves through, and leaves your system:

```
[User Browser] --HTTPS--> [API Gateway] --mTLS--> [User Service]
                                                       |
                                                       v
                                                  [PostgreSQL]
                                                       |
                                                       v
                                              [Backup Storage (S3)]
```

For each flow, document:
- **Source**: Where data originates (user input, third-party API, sensor)
- **Transport**: Protocol and encryption (HTTPS, mTLS, plaintext)
- **Processing**: What operations are performed (storage, aggregation, inference)
- **Storage**: Where data rests (database, cache, filesystem, logs)
- **Retention**: How long data is kept before deletion
- **Cross-border transfers**: Whether data leaves the EU/EEA

### Step 3: Implement PII detection

Scan your codebase and data stores for unclassified personal data:

- **Database columns**: Audit column names for PII indicators (name, email, phone, address,
  dob, ssn, ip_address).
- **Log files**: Search for patterns that match email addresses, IP addresses, phone numbers.
  These should be masked or excluded from logs.
- **Configuration**: Check for personal data in config files, environment variables, or
  hardcoded test fixtures.

### Step 4: Define retention and deletion

Every personal data field needs:
1. A defined retention period justified by its purpose.
2. An automated deletion mechanism (cron job, TTL, lifecycle policy).
3. A manual deletion path for DSAR "right to erasure" requests.

## Prevention

**CI-enforceable checks:**

```yaml
data-classification-check:
  stage: lint
  script:
    # Verify classification file exists and is valid
    - test -f data-classification.yaml
        || (echo "ERROR: data-classification.yaml missing" && exit 1)
    - python scripts/validate_classification.py data-classification.yaml
    # Scan for potential PII in log statements
    - |
      grep -rn --include="*.py" \
        -E 'log\.(info|debug|warning|error).*\b(email|password|ssn|phone)\b' src/ \
        && echo "WARNING: Potential PII in log statements" && exit 1 || true
  rules:
    - if: $CI_PIPELINE_SOURCE == "merge_request_event"
```

**Process:**

- Maintain a `data-classification.yaml` at the project root listing every personal data field,
  its tier, purpose, retention, and legal basis.
- Require DPO (Data Protection Officer) review for any MR that introduces T3/T4 data fields.
- Run automated PII scans against database schemas and log output periodically.
- Include data classification in the definition of done for features that handle user data.
- Review and update the data flow map quarterly or when architecture changes.
