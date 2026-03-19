---
title: "Fix: AI Act Risk Classification"
status: current
last-updated: 2026-03-19
instrument: compliance-tomographe
severity-range: "Major–Critical"
---

# Fix: AI Act Risk Classification

## What this means

Your project includes an AI system (machine learning model, automated decision-making, or
algorithmic processing) that has not been classified under the EU AI Act (Regulation 2024/1689).
The AI Act requires providers and deployers of AI systems to assess risk level, implement
proportionate controls, and maintain technical documentation. Failure to classify means you
cannot determine your compliance obligations, and deploying an unclassified high-risk system
carries penalties of up to 3% of global annual turnover or EUR 15 million.

## How to fix

### Step 1: Determine risk tier

| Risk Tier | Description | Examples | Key Obligations |
|---|---|---|---|
| **Unacceptable** | Banned outright | Social scoring, manipulative AI | Prohibited |
| **High-Risk** | Annex III or safety-component | Medical devices, recruitment, credit scoring | Conformity assessment, risk mgmt, human oversight, docs |
| **Limited Risk** | Transparency obligations | Chatbots, emotion recognition, deepfakes | Disclosure to users |
| **Minimal Risk** | No specific obligations | Spam filters, game AI, recommendations | Voluntary codes |

**Annex III high-risk categories (abridged):**

1. Biometric identification and categorisation
2. Critical infrastructure management
3. Education and vocational training (access, assessment)
4. Employment, recruitment, worker management
5. Essential services access (credit, insurance, social benefits)
6. Law enforcement (risk assessment, evidence evaluation)
7. Migration, asylum, border control
8. Administration of justice

### Python

```python
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class AIRiskTier(Enum):
    UNACCEPTABLE = "unacceptable"
    HIGH = "high"
    LIMITED = "limited"
    MINIMAL = "minimal"


@dataclass
class AISystemCard:
    """Documentation card for an AI system under the EU AI Act."""

    system_name: str
    version: str
    risk_tier: AIRiskTier
    intended_purpose: str
    annex_iii_category: str | None
    provider: str
    risk_management_plan: str | None = None
    human_oversight_mechanism: str | None = None
    training_data_description: str | None = None
    performance_metrics: dict[str, float] | None = None
    logging_enabled: bool = False

    def validate(self) -> list[str]:
        issues = []
        if self.risk_tier == AIRiskTier.UNACCEPTABLE:
            issues.append(f"'{self.system_name}' is prohibited (Art. 5)")
        if self.risk_tier == AIRiskTier.HIGH:
            if not self.risk_management_plan:
                issues.append("Risk management plan required (Art. 9)")
            if not self.human_oversight_mechanism:
                issues.append("Human oversight mechanism required (Art. 14)")
            if not self.training_data_description:
                issues.append("Training data documentation required (Art. 10)")
            if not self.logging_enabled:
                issues.append("Automatic event logging required (Art. 12)")
            if not self.annex_iii_category:
                issues.append("Must specify Annex III category")
        return issues
```

### Rust

```rust
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum AiRiskTier { Unacceptable, High, Limited, Minimal }

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AiSystemCard {
    pub system_name: String,
    pub version: String,
    pub risk_tier: AiRiskTier,
    pub intended_purpose: String,
    pub annex_iii_category: Option<String>,
    pub provider: String,
    pub risk_management_plan: Option<String>,
    pub human_oversight_mechanism: Option<String>,
    pub training_data_description: Option<String>,
    pub logging_enabled: bool,
}

impl AiSystemCard {
    pub fn validate(&self) -> Vec<String> {
        let mut issues = Vec::new();
        if matches!(self.risk_tier, AiRiskTier::Unacceptable) {
            issues.push(format!("'{}' is prohibited (Art. 5)", self.system_name));
        }
        if matches!(self.risk_tier, AiRiskTier::High) {
            if self.risk_management_plan.is_none() {
                issues.push("Risk management plan required (Art. 9)".into());
            }
            if self.human_oversight_mechanism.is_none() {
                issues.push("Human oversight required (Art. 14)".into());
            }
            if self.training_data_description.is_none() {
                issues.push("Training data docs required (Art. 10)".into());
            }
            if !self.logging_enabled {
                issues.push("Automatic logging required (Art. 12)".into());
            }
        }
        issues
    }
}
```

### TypeScript

```typescript
type AiRiskTier = "unacceptable" | "high" | "limited" | "minimal";

interface AiSystemCard {
  systemName: string;
  version: string;
  riskTier: AiRiskTier;
  intendedPurpose: string;
  annexIiiCategory?: string;
  provider: string;
  riskManagementPlan?: string;
  humanOversightMechanism?: string;
  trainingDataDescription?: string;
  loggingEnabled: boolean;
}

function validateAiSystemCard(card: AiSystemCard): string[] {
  const issues: string[] = [];
  if (card.riskTier === "unacceptable")
    issues.push(`'${card.systemName}' is prohibited (Art. 5)`);
  if (card.riskTier === "high") {
    if (!card.riskManagementPlan)
      issues.push("Risk management plan required (Art. 9)");
    if (!card.humanOversightMechanism)
      issues.push("Human oversight required (Art. 14)");
    if (!card.loggingEnabled)
      issues.push("Automatic logging required (Art. 12)");
  }
  return issues;
}
```

### Go

```go
package aiact

import "fmt"

type AiRiskTier string

const (
    TierUnacceptable AiRiskTier = "unacceptable"
    TierHigh         AiRiskTier = "high"
    TierLimited      AiRiskTier = "limited"
    TierMinimal      AiRiskTier = "minimal"
)

type AiSystemCard struct {
    SystemName              string  `yaml:"system_name"`
    Version                 string  `yaml:"version"`
    RiskTier                AiRiskTier `yaml:"risk_tier"`
    IntendedPurpose         string  `yaml:"intended_purpose"`
    AnnexIIICategory        string  `yaml:"annex_iii_category,omitempty"`
    Provider                string  `yaml:"provider"`
    RiskManagementPlan      string  `yaml:"risk_management_plan,omitempty"`
    HumanOversightMechanism string  `yaml:"human_oversight,omitempty"`
    LoggingEnabled          bool    `yaml:"logging_enabled"`
}

func (c *AiSystemCard) Validate() []string {
    var issues []string
    if c.RiskTier == TierUnacceptable {
        issues = append(issues, fmt.Sprintf(
            "'%s' is prohibited (Art. 5)", c.SystemName))
    }
    if c.RiskTier == TierHigh {
        if c.RiskManagementPlan == "" {
            issues = append(issues, "risk management plan required (Art. 9)")
        }
        if c.HumanOversightMechanism == "" {
            issues = append(issues, "human oversight required (Art. 14)")
        }
        if !c.LoggingEnabled {
            issues = append(issues, "automatic logging required (Art. 12)")
        }
    }
    return issues
}
```

### General

**Technical documentation for high-risk systems** (Art. 11) must cover:

1. **General description**: Purpose, intended use, foreseeable misuse
2. **Risk management**: Identified risks, mitigations, residual risks
3. **Data governance**: Training data sources, preprocessing, bias assessment
4. **Performance**: Accuracy and fairness metrics across demographic groups
5. **Human oversight**: How operators can intervene, override, or shut down
6. **Logging**: Events recorded, retention period, access controls

**Human oversight mechanisms** (Art. 14) -- implement at least one:

- **Human-in-the-loop**: Human approves every decision before execution
- **Human-on-the-loop**: Human monitors and can intervene on any decision
- **Human-in-command**: Human can override or shut down the system at any time

At minimum, implement a kill switch, audit logging of all decisions with confidence scores,
alerting when confidence drops below threshold, and a review queue for high-risk decisions.

**Conformity assessment** (Art. 43) for Annex III systems:

- Conduct internal conformity assessment
- Register in the EU database (Art. 49) before market placement
- Maintain documentation for 10 years
- Appoint an EU authorised representative if provider is outside the EU

## Prevention

**CI-enforceable checks:**

```yaml
ai-act-compliance:
  stage: lint
  script:
    - test -f ai-system-card.yaml
        || (echo "ERROR: ai-system-card.yaml missing" && exit 1)
    - python scripts/validate_ai_card.py ai-system-card.yaml
  rules:
    - if: $CI_PIPELINE_SOURCE == "merge_request_event"
      changes:
        - "ai-system-card.yaml"
        - "models/**"
        - "src/ml/**"
```

**Process:**

- Create an `ai-system-card.yaml` at the project root for each AI system.
- Review risk classification when model purpose, training data, or deployment context changes.
- Assign a compliance owner for high-risk systems.
- Include AI Act review in MR checklists for ML component changes.
- Schedule quarterly reviews of classification and documentation completeness.
