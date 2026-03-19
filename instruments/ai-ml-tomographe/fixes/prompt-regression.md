---
title: "Fix: Prompt Regression"
status: current
last-updated: 2026-03-19
instrument: ai-ml-tomographe
severity-range: "Major"
---

# Fix: Prompt Regression

## What this means

A change to a prompt template, system instruction, or LLM configuration has degraded output
quality compared to the previous version. This can manifest as incorrect classifications,
lower-quality summaries, hallucinated content, format violations, or changed tone. Prompt
regressions are particularly insidious because they are invisible to traditional test suites —
the code compiles, the API returns 200, but the output is worse. Without prompt versioning and
automated evaluation, regressions are only caught when users report degraded quality, often
days or weeks after the change shipped.

## How to fix

### Python

**Version prompts as structured files, not inline strings:**

```python
# prompts/classifier_v2.yaml
version: "2.0.0"
name: classifier
description: "Classify customer support tickets into categories"
model: gpt-4o-mini
temperature: 0.0
system: |
  You are a customer support ticket classifier. Classify each ticket into
  exactly one of these categories: authentication, billing, bug_report,
  feature_request, general_inquiry.

  Rules:
  - Respond with ONLY the category name, no explanation.
  - If the ticket could fit multiple categories, choose the most specific one.
  - If the ticket doesn't fit any category, respond with "general_inquiry".
user_template: |
  Classify this support ticket:

  {ticket_text}
```

```python
# prompts/loader.py
"""Load and version-track prompt templates."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml


PROMPTS_DIR = Path(__file__).parent


@dataclass
class PromptTemplate:
    version: str
    name: str
    description: str
    model: str
    temperature: float
    system: str
    user_template: str

    @classmethod
    def load(cls, name: str, version: str | None = None) -> PromptTemplate:
        """Load a prompt template by name.

        If version is None, loads the latest version found on disk.
        """
        if version:
            path = PROMPTS_DIR / f"{name}_v{version.split('.')[0]}.yaml"
        else:
            # Find latest version file
            candidates = sorted(PROMPTS_DIR.glob(f"{name}_v*.yaml"))
            if not candidates:
                raise FileNotFoundError(
                    f"No prompt template found for '{name}' in {PROMPTS_DIR}"
                )
            path = candidates[-1]

        data = yaml.safe_load(path.read_text())
        return cls(**data)

    def render(self, **kwargs: str) -> str:
        """Render the user message template with provided variables."""
        return self.user_template.format(**kwargs)
```

**Prompt evaluation with promptfoo:**

```bash
# Install promptfoo
npm install -g promptfoo

# Initialise config
promptfoo init
```

```yaml
# promptfooconfig.yaml
description: "Classifier prompt evaluation"

prompts:
  - file://prompts/classifier_v1.yaml
  - file://prompts/classifier_v2.yaml

providers:
  - id: openai:gpt-4o-mini
    config:
      temperature: 0

tests:
  - vars:
      ticket_text: "I can't log into my account after resetting my password"
    assert:
      - type: equals
        value: authentication

  - vars:
      ticket_text: "You charged me twice for last month's subscription"
    assert:
      - type: equals
        value: billing

  - vars:
      ticket_text: "The export button crashes when I click it"
    assert:
      - type: equals
        value: bug_report

  - vars:
      ticket_text: "Can you add dark mode to the dashboard?"
    assert:
      - type: equals
        value: feature_request

  - vars:
      ticket_text: "What are your business hours?"
    assert:
      - type: equals
        value: general_inquiry

  # Edge cases
  - vars:
      ticket_text: "I was charged twice AND I can't log in to dispute it"
    assert:
      - type: equals
        value: billing
    description: "Multi-category: billing takes priority over auth"
```

```bash
# Run evaluation — shows side-by-side comparison of v1 vs v2
promptfoo eval

# Generate a shareable report
promptfoo eval --output results.json
promptfoo view
```

**Custom pytest-based prompt regression suite:**

```python
# tests/eval/test_prompt_regression.py
"""Prompt regression tests — compare current vs baseline outputs."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from myapp.llm_client import call_llm
from prompts.loader import PromptTemplate


BASELINE_PATH = Path("tests/eval/baselines/classifier_v1_results.json")
CURRENT_PROMPT = PromptTemplate.load("classifier")


@pytest.fixture(scope="module")
def baseline_results() -> dict[str, str]:
    """Load baseline results from the previous known-good prompt version."""
    return json.loads(BASELINE_PATH.read_text())


@pytest.fixture(scope="module")
def current_results(golden_examples) -> dict[str, str]:
    """Run the current prompt against all golden examples."""
    results = {}
    for ex in golden_examples:
        response = call_llm(
            model=CURRENT_PROMPT.model,
            system=CURRENT_PROMPT.system,
            user=CURRENT_PROMPT.render(ticket_text=ex["input"]),
            temperature=CURRENT_PROMPT.temperature,
        )
        results[ex["id"]] = response.strip()
    return results


def test_no_regression_in_correct_answers(baseline_results, current_results):
    """Examples that passed with the baseline must still pass."""
    regressions = []
    for example_id, baseline_output in baseline_results.items():
        current_output = current_results.get(example_id)
        if current_output is None:
            continue
        if baseline_output == current_output:
            continue
        # Only flag as regression if baseline was correct
        # (improvements are fine)
        regressions.append({
            "id": example_id,
            "baseline": baseline_output,
            "current": current_output,
        })

    assert not regressions, (
        f"{len(regressions)} regressions detected:\n"
        + "\n".join(
            f"  [{r['id']}] was '{r['baseline']}', now '{r['current']}'"
            for r in regressions[:10]
        )
    )


def test_overall_quality_not_degraded(baseline_results, current_results, golden_examples):
    """Current prompt must match or exceed baseline pass rate."""
    expected = {ex["id"]: ex["expected_output"] for ex in golden_examples}

    baseline_correct = sum(
        1 for eid, out in baseline_results.items()
        if expected.get(eid) == out
    )
    current_correct = sum(
        1 for eid, out in current_results.items()
        if expected.get(eid) == out
    )

    baseline_rate = baseline_correct / len(baseline_results)
    current_rate = current_correct / len(current_results)

    assert current_rate >= baseline_rate - 0.02, (
        f"Quality degraded: baseline {baseline_rate:.1%}, "
        f"current {current_rate:.1%} (max allowed drop: 2%)"
    )
```

**Generate and update baselines:**

```python
# scripts/update_baseline.py
"""Generate baseline results for the current prompt version.

Run this after validating that the current prompt produces acceptable quality.
The baseline is committed to git and used by regression tests.
"""
from __future__ import annotations

import json
from pathlib import Path

from eval.golden_dataset import GoldenDataset
from myapp.llm_client import call_llm
from prompts.loader import PromptTemplate


def main() -> None:
    prompt = PromptTemplate.load("classifier")
    dataset = GoldenDataset.load(Path("eval/data/golden_v1.json"))

    results = {}
    for ex in dataset.examples:
        response = call_llm(
            model=prompt.model,
            system=prompt.system,
            user=prompt.render(ticket_text=ex.input),
            temperature=prompt.temperature,
        )
        results[ex.id] = response.strip()
        print(f"  {ex.id}: {results[ex.id]}")

    output_path = Path(
        f"tests/eval/baselines/classifier_v{prompt.version.split('.')[0]}"
        f"_results.json"
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(results, indent=2))
    print(f"\nBaseline saved to {output_path}")


if __name__ == "__main__":
    main()
```

### General

**Prompt versioning strategy:**

```
prompts/
├── classifier_v1.yaml      # Original version (retired)
├── classifier_v2.yaml      # Current production version
├── classifier_v3.yaml      # Candidate under evaluation
├── summariser_v1.yaml
└── CHANGELOG.md             # Document what changed and why
```

Versioning rules:
- **Patch** (1.0.0 -> 1.0.1): Typo fixes, whitespace changes with no semantic impact.
- **Minor** (1.0.0 -> 1.1.0): Added examples, clarified instructions, same expected
  behaviour.
- **Major** (1.0.0 -> 2.0.0): Changed output format, added/removed categories, different
  model, changed system behaviour.

**A/B evaluation workflow:**

1. **Create the candidate prompt** as a new version file (e.g., `classifier_v3.yaml`).
2. **Run evaluation** against the golden dataset for both current and candidate.
3. **Compare metrics side-by-side:** pass rate, per-category accuracy, latency, cost.
4. **Review regressions:** any example that passed with v2 but fails with v3 must be
   individually reviewed and justified.
5. **Gate on quality:** candidate must match or exceed current on aggregate metrics.
   Individual regressions are acceptable only if offset by larger gains elsewhere and
   explicitly documented.
6. **Promote:** once approved, update the production reference to the new version.

**Prompt diff tooling:**

```bash
# Simple text diff between prompt versions
diff prompts/classifier_v1.yaml prompts/classifier_v2.yaml

# Semantic diff with promptfoo
promptfoo eval --prompt prompts/classifier_v1.yaml prompts/classifier_v2.yaml

# Git-based prompt history
git log --oneline --follow prompts/classifier_v2.yaml
```

**Evaluation metrics for prompt quality:**

| Metric | When to use | How to compute |
|---|---|---|
| Exact match | Classification, extraction | `actual == expected` |
| Contains | Required keywords/phrases | `keyword in actual` |
| JSON validity | Structured output | `json.loads(actual)` succeeds |
| Schema match | Structured output | JSON Schema validation |
| Semantic similarity | Generative text | BERTScore, cosine on embeddings |
| LLM-as-judge | Open-ended generation | Second LLM rates quality 1-5 |
| Latency | All | Response time in milliseconds |
| Token count | Cost optimisation | Input + output token count |

## Prevention

**CI pipeline for prompt changes:**

```yaml
# GitLab CI
prompt-regression:
  stage: test
  image: python:3.11-slim
  script:
    - pip install -r requirements-eval.txt
    - pytest tests/eval/test_prompt_regression.py -v --tb=short
  rules:
    - if: $CI_PIPELINE_SOURCE == "merge_request_event"
      changes:
        - "prompts/**/*"
        - "src/llm_client.py"
        - "src/pipeline.py"
  allow_failure: false

prompt-eval-full:
  stage: test
  image: node:20-slim
  script:
    - npm install -g promptfoo
    - promptfoo eval --output results.json
    - >
      node -e "
        const r = require('./results.json');
        const pass = r.results.stats.successes;
        const total = r.results.stats.successes + r.results.stats.failures;
        const rate = pass / total;
        console.log('Pass rate:', (rate * 100).toFixed(1) + '%');
        if (rate < 0.85) process.exit(1);
      "
  rules:
    - if: $CI_PIPELINE_SOURCE == "merge_request_event"
      changes:
        - "prompts/**/*"
  allow_failure: false
```

**Process rules:**

- Every prompt change requires running the evaluation suite before merge. Results
  (pass rate, regressions) must be included in the MR description.
- Prompt files are treated as code: they live in version control, require review,
  and follow SemVer.
- Never edit a production prompt in-place. Create a new version, evaluate, promote.
- Maintain a prompt changelog documenting what changed, why, and evaluation results.
- Baseline results are committed to git. After promoting a new prompt version, regenerate
  and commit the new baseline.
- Schedule weekly full evaluation runs against the golden dataset to detect drift from
  model provider changes (model updates, API behaviour changes).
