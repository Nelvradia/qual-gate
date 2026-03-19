---
title: "Fix: Missing Golden Datasets"
status: current
last-updated: 2026-03-19
instrument: ai-ml-tomographe
severity-range: "Major"
---

# Fix: Missing Golden Datasets

## What this means

Your AI/ML pipeline lacks a curated, version-controlled evaluation dataset with known-correct
outputs (a "golden dataset"). Without one, you cannot reliably measure model quality, detect
regressions between releases, or compare alternative approaches. Every change to the model,
prompt, retrieval pipeline, or post-processing logic becomes a leap of faith. Regressions ship
silently because there is no baseline to compare against. A golden dataset is the equivalent of
a test suite for deterministic code — without it, you are deploying untested software.

## How to fix

### Python

**Create a golden dataset structure:**

```python
# eval/golden_dataset.py
"""Golden dataset management for evaluation harnesses."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class GoldenExample:
    """A single evaluation example with input, expected output, and metadata."""

    id: str
    input: str
    expected_output: str
    category: str  # e.g., "summarisation", "classification", "extraction"
    tags: list[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)


@dataclass
class GoldenDataset:
    """Version-controlled collection of evaluation examples."""

    version: str
    description: str
    examples: list[GoldenExample]

    @classmethod
    def load(cls, path: Path) -> GoldenDataset:
        data = json.loads(path.read_text())
        examples = [GoldenExample(**ex) for ex in data["examples"]]
        return cls(
            version=data["version"],
            description=data["description"],
            examples=examples,
        )

    def save(self, path: Path) -> None:
        data = {
            "version": self.version,
            "description": self.description,
            "examples": [
                {
                    "id": ex.id,
                    "input": ex.input,
                    "expected_output": ex.expected_output,
                    "category": ex.category,
                    "tags": ex.tags,
                    "metadata": ex.metadata,
                }
                for ex in self.examples
            ],
        }
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False))

    def filter_by_category(self, category: str) -> list[GoldenExample]:
        return [ex for ex in self.examples if ex.category == category]
```

**pytest-based evaluation harness:**

```python
# tests/eval/test_golden_dataset.py
"""Regression tests against the golden dataset."""
from __future__ import annotations

import pytest

from eval.golden_dataset import GoldenDataset
from myapp.pipeline import run_pipeline  # Your actual pipeline


GOLDEN_PATH = Path("eval/data/golden_v1.json")
DATASET = GoldenDataset.load(GOLDEN_PATH)


@pytest.fixture
def pipeline():
    """Initialise the pipeline once per test session."""
    return run_pipeline  # or an initialised pipeline object


@pytest.mark.parametrize(
    "example",
    DATASET.examples,
    ids=[ex.id for ex in DATASET.examples],
)
def test_golden_example(pipeline, example):
    """Each golden example must produce output matching expected within threshold."""
    actual = pipeline(example.input)

    # Exact match for classification tasks
    if example.category == "classification":
        assert actual == example.expected_output, (
            f"[{example.id}] Expected '{example.expected_output}', "
            f"got '{actual}'"
        )
        return

    # Similarity-based match for generative tasks
    similarity = compute_similarity(actual, example.expected_output)
    threshold = example.metadata.get("similarity_threshold", 0.85)
    assert similarity >= threshold, (
        f"[{example.id}] Similarity {similarity:.3f} below threshold "
        f"{threshold}. Expected: '{example.expected_output[:80]}...', "
        f"got: '{actual[:80]}...'"
    )


def compute_similarity(actual: str, expected: str) -> float:
    """Compute semantic similarity between two texts.

    Replace with your preferred metric: ROUGE, BERTScore, cosine similarity
    on embeddings, or exact match ratio.
    """
    # Simple token overlap as a placeholder — use a real metric in production
    actual_tokens = set(actual.lower().split())
    expected_tokens = set(expected.lower().split())
    if not expected_tokens:
        return 1.0 if not actual_tokens else 0.0
    return len(actual_tokens & expected_tokens) / len(expected_tokens)
```

**Aggregate evaluation metrics:**

```python
# tests/eval/test_aggregate_metrics.py
"""Aggregate quality metrics across the golden dataset."""
from __future__ import annotations

import pytest

from eval.golden_dataset import GoldenDataset
from myapp.pipeline import run_pipeline


GOLDEN_PATH = Path("eval/data/golden_v1.json")
DATASET = GoldenDataset.load(GOLDEN_PATH)

# Minimum pass rates per category — adjust per project
CATEGORY_THRESHOLDS = {
    "classification": 0.95,   # 95% must match exactly
    "summarisation": 0.80,    # 80% must exceed similarity threshold
    "extraction": 0.90,       # 90% must match exactly
}


def test_aggregate_pass_rate():
    """Overall pass rate must meet minimum threshold."""
    results = []
    for ex in DATASET.examples:
        actual = run_pipeline(ex.input)
        passed = evaluate_example(actual, ex)
        results.append({"id": ex.id, "category": ex.category, "passed": passed})

    total = len(results)
    passed = sum(1 for r in results if r["passed"])
    rate = passed / total if total > 0 else 0

    assert rate >= 0.85, (
        f"Overall pass rate {rate:.1%} ({passed}/{total}) "
        f"below minimum threshold 85%"
    )

    # Per-category breakdown
    for category, threshold in CATEGORY_THRESHOLDS.items():
        cat_results = [r for r in results if r["category"] == category]
        if not cat_results:
            continue
        cat_passed = sum(1 for r in cat_results if r["passed"])
        cat_rate = cat_passed / len(cat_results)
        assert cat_rate >= threshold, (
            f"Category '{category}' pass rate {cat_rate:.1%} "
            f"({cat_passed}/{len(cat_results)}) below threshold {threshold:.0%}"
        )
```

**Dataset versioning with DVC:**

```bash
# Install DVC (Data Version Control)
pip install dvc

# Initialise DVC in the repo
dvc init

# Track the golden dataset
dvc add eval/data/golden_v1.json

# The .dvc file is committed to git; the data file is stored in remote storage
git add eval/data/golden_v1.json.dvc eval/data/.gitignore
git commit -m "data: add golden dataset v1"

# Configure remote storage (S3, GCS, Azure, SSH, local)
dvc remote add -d storage s3://my-bucket/dvc-store
dvc push
```

### General

**Golden dataset structure:**

```
eval/
├── data/
│   ├── golden_v1.json          # Current golden dataset
│   ├── golden_v1.json.dvc      # DVC tracking file (committed to git)
│   └── README.md               # Dataset documentation
├── golden_dataset.py           # Dataset loading/management
├── metrics.py                  # Evaluation metric implementations
└── reports/                    # Generated evaluation reports
```

**Golden dataset JSON schema:**

```json
{
  "version": "1.0.0",
  "description": "Golden evaluation dataset for customer support classifier",
  "created": "2026-03-19",
  "examples": [
    {
      "id": "cls-001",
      "input": "I can't log into my account",
      "expected_output": "authentication",
      "category": "classification",
      "tags": ["login", "auth"],
      "metadata": {
        "source": "production_sample_2026Q1",
        "annotator": "team_lead",
        "confidence": "high"
      }
    }
  ]
}
```

**Building your golden dataset — methodology:**

1. **Sample from production data.** Select 100-500 representative examples across all
   categories your system handles. Over-sample edge cases and failure modes.
2. **Annotate with domain experts.** Each example needs a verified correct output. For
   ambiguous cases, include multiple acceptable outputs or mark as "flexible" with a
   similarity threshold.
3. **Stratify by difficulty.** Include easy (baseline), medium (typical), and hard (edge
   case) examples. Tag each with difficulty level so you can track where regressions
   happen.
4. **Version the dataset.** Use SemVer: patch for typo fixes, minor for adding examples,
   major for schema changes or re-annotation.
5. **Review periodically.** Golden datasets rot when the domain changes. Schedule quarterly
   reviews to retire outdated examples and add new ones from recent production data.

**Evaluation metrics by task type:**

| Task | Metric | Threshold (typical) |
|---|---|---|
| Classification | Accuracy, F1, confusion matrix | >= 95% accuracy |
| Extraction | Exact match, token-level F1 | >= 90% exact match |
| Summarisation | ROUGE-L, BERTScore | >= 0.80 ROUGE-L |
| Generation (open) | Human eval, LLM-as-judge | >= 4.0/5.0 average |
| Retrieval | Recall@k, MRR | >= 0.85 Recall@10 |

## Prevention

**CI pipeline for evaluation:**

```yaml
# GitLab CI
eval-golden:
  stage: test
  image: python:3.11-slim
  script:
    - pip install -r requirements-eval.txt
    - dvc pull eval/data/
    - pytest tests/eval/ -v --tb=short --junitxml=eval-report.xml
  artifacts:
    reports:
      junit: eval-report.xml
    expire_in: 1 week
  allow_failure: false
  rules:
    - if: $CI_PIPELINE_SOURCE == "merge_request_event"
      changes:
        - "src/**/*"
        - "prompts/**/*"
        - "eval/**/*"
```

**Process rules:**

- No model, prompt, or pipeline change merges without passing the golden dataset evaluation.
- Golden dataset changes require review by a domain expert, not just a developer.
- Evaluation results (pass rate, per-category breakdown) must be included in every MR
  description that touches the AI/ML pipeline.
- Track evaluation metrics over time in a dashboard. Alert on any regression > 2% from
  the previous release baseline.
- New failure modes discovered in production are added to the golden dataset within the
  same sprint as the fix.
