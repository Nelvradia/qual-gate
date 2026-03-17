# ai-ml-tomographe

**AI/ML quality scanner for the target project.** Evaluates LLM extraction quality, RAG retrieval health, golden dataset integrity, prompt regression, model routing accuracy, and confidence calibration. Covers AI-specific concerns that standard review templates don't have a section for.

**Covers DR Sections:** None in current template — this instrument defines a **new quality dimension** for AI-native systems. Feeds into accuracy targets and test mandates.

---

## Quick Start

```bash
"Read instruments/ai-ml-tomographe/README.md and execute a full AI/ML quality scan."
"Read instruments/ai-ml-tomographe/README.md and execute Phase 1 (Golden Datasets) only."
```

---

## Scan Phases

| Phase | Name | What It Does | Requires LLM? |
|-------|------|-------------|---------------|
| **1** | Golden Datasets | Validate schema, count, balance, completeness | No |
| **2** | Extraction Quality | Measure accuracy against golden datasets | Yes (or cached results) |
| **3** | RAG Retrieval | Evaluate search quality — recall, precision, MRR | Yes |
| **4** | Prompt Health | Track AI behaviour configuration versions, system prompt integrity, regression risk | No |
| **5** | Model Routing | Verify tier classification accuracy if router deployed | Yes |
| **6** | Confidence Calibration | Check predicted confidence vs actual correctness | Yes (or cached) |
| **7** | Report | Compile AI/ML health report | No |

---

## Phase 1 — Golden Datasets (No LLM Required)

**Goal:** Validate the integrity of evaluation datasets.

```bash
# Dataset existence and size
for dataset in corrections summaries classifications templates; do
  file="tests/fixtures/golden/${dataset}_golden.jsonl"
  if [ -f "$file" ]; then
    lines=$(wc -l < "$file")
    echo "OK: $file — $lines examples"
  else
    echo "MISSING: $file"
  fi
done

# Schema validation (each line must be valid JSON)
for file in tests/fixtures/golden/*.jsonl; do
  invalid=$(while read line; do echo "$line" | jq empty 2>&1 | grep -c 'error'; done < "$file")
  echo "$file: $invalid invalid lines out of $(wc -l < "$file")"
done

# Category balance
for file in tests/fixtures/golden/*.jsonl; do
  echo "=== $file ==="
  jq -r '.category // .type // .class // "uncategorized"' "$file" 2>/dev/null | sort | uniq -c | sort -rn
done

# Run validation script if available
python3 scripts/validate_golden_datasets.py \
  --golden-dir tests/fixtures/golden/ 2>/dev/null

# Check minimum examples per accuracy targets
echo "Target minimums: corrections>=50, summaries>=30, classifications>=40, templates>=20"
```

### Severity Rules

| Finding | Severity |
|---------|----------|
| Golden dataset file missing | **Major** |
| Dataset below minimum example count | **Minor** |
| Invalid JSON lines in dataset | **Major** |
| Category imbalance >60% one type | **Minor** |
| Validation script missing or broken | **Minor** |

---

## Phase 2 — Extraction Quality (LLM Required)

**Goal:** Measure accuracy of LLM extractions against golden datasets.

```bash
# Run evaluation if script exists and LLM is available
python3 scripts/evaluate_extractions.py \
  --golden-dir tests/fixtures/golden/ \
  --output output/extraction-results.json 2>/dev/null

# If LLM not available, check for cached results
if [ -f output/extraction-results.json ]; then
  echo "Using cached extraction results"
  cat output/extraction-results.json | jq '.summary'
else
  echo "NO_RESULTS: Extraction evaluation requires running LLM"
fi
```

### Accuracy Targets

| Extraction Type | Metric | Target |
|---|---|---|
| Correction detection | Precision | >=90% |
| Correction detection | Recall | >=80% |
| Correction classification | Accuracy | >=85% |
| Conversation summary | Key-point recall | >=80% |
| Thread detection | Accuracy | >=80% |
| Template extraction | Variable recall | >=80% |
| Notification classification | Action-required accuracy | >=90% |
| Communication tone | Tone match | >=85% |

---

## Phase 3 — RAG Retrieval (LLM Required)

**Goal:** Evaluate semantic search quality.

```bash
# Check eval dataset existence
if [ -f tests/fixtures/rag_eval/queries.jsonl ]; then
  echo "RAG eval dataset: $(wc -l < tests/fixtures/rag_eval/queries.jsonl) query-document pairs"
else
  echo "ABSENT: No RAG evaluation dataset"
fi

# Check vector store is accessible
curl -sf http://localhost:6333/collections 2>/dev/null | jq '.result.collections | length'

# If eval dataset and vector store available, run evaluation:
# 1. For each query in eval dataset
# 2. Send to vector store search
# 3. Compare retrieved docs against expected docs
# 4. Compute Recall@K, Precision@K, MRR

# Check for existing eval results
cat output/rag-eval-results.json 2>/dev/null | jq '.summary'
```

### Readiness Assessment

| Component | Status |
|---|---|
| Eval dataset exists (>=50 pairs) | |
| Evaluation script exists | |
| Vector store accessible | |
| Baseline measurement exists | |
| Quality threshold defined (Recall@10 >= 0.8) | |

---

## Phase 4 — Prompt Health (No LLM Required)

**Goal:** Track prompt versioning and regression risk.

```bash
# AI behaviour configuration file version tracking
# Locate personality/system prompt configuration files
find . -name '*.md' -path '*/personality/*' -o -name '*system-prompt*' 2>/dev/null

# Hash configuration files for change detection
for f in $(find . -name '*system-prompt*' -o -name '*personality*' 2>/dev/null); do
  hash=$(sha256sum "$f" 2>/dev/null | cut -c1-16)
  echo "$f hash: ${hash:-NOT_FOUND}"
done

# Track changes since last scan
git log --oneline -5 -- '**/personality/**' '**/system-prompt*' 2>/dev/null

# System prompt construction
grep -rn 'system_prompt\|system_message\|SystemMessage' src/ --include='*.rs' --include='*.py' | wc -l

# Prompt template locations
find src/ config/ -name '*.txt' -o -name '*prompt*' -o -name '*template*' 2>/dev/null | \
  grep -v 'test\|node_modules\|target'

# Check if prompt changes are version-controlled
git log --oneline -10 -- '**/prompt*' '**/personality*' 'config/**/prompt*' 2>/dev/null
```

### Checklist

- [ ] AI behaviour configuration files exist and have content
- [ ] Extended configuration exists (if applicable)
- [ ] System prompt construction is centralized (not scattered across modules)
- [ ] Prompt changes tracked in git history
- [ ] Hash/version tracking mechanism exists (for regression detection)
- [ ] Configuration changes trigger quality evaluation (manual or automated)

---

## Phase 5 — Model Routing (LLM Required)

**Goal:** Verify the model tier router classifies requests correctly.

```bash
# Check if router is deployed
grep -rn 'router\|Router\|model_select\|tier_select' src/ --include='*.rs' --include='*.py' | head -10

# Check for routing config
grep -rn 'routing\|model_tier\|model_selection' config/ --include='*.yaml' | head -10

# If routing test dataset exists:
if [ -f tests/fixtures/routing/labeled_requests.jsonl ]; then
  echo "Routing dataset: $(wc -l < tests/fixtures/routing/labeled_requests.jsonl) labeled requests"
else
  echo "NOT_DEPLOYED: Router not yet active or no test dataset"
fi
```

**Note:** Model routing may not yet be deployed. This phase will return N/A until the router goes live. Pre-building the dataset and evaluation framework now prevents regression when it ships.

---

## Phase 6 — Confidence Calibration (LLM Required)

**Goal:** Verify that confidence scores match actual correctness rates.

```bash
# Check for calibration data
if [ -f output/calibration-data.json ]; then
  echo "Calibration data available"
  jq '.data_points | length' output/calibration-data.json
else
  echo "NO_DATA: Confidence calibration requires accumulated (confidence, correctness) pairs"
fi

# Check confidence field exists in extraction outputs
grep -rn 'confidence\|Confidence' src/ --include='*.rs' --include='*.py' | head -10
```

**Note:** Calibration requires accumulated data from production use. Until sufficient data exists (>=100 data points recommended), this phase produces a readiness assessment rather than actual calibration results.

---

## Configuration

```yaml
thresholds:
  golden_datasets:
    corrections_min: 50
    summaries_min: 30
    classifications_min: 40
    templates_min: 20
    max_category_imbalance: 0.60
  extraction_quality:
    correction_precision: 0.90
    correction_recall: 0.80
    classification_accuracy: 0.85
    summary_recall: 0.80
    template_recall: 0.80
  rag:
    eval_pairs_min: 50
    recall_at_10: 0.80
    mrr_min: 0.60
  routing:
    accuracy_min: 0.90
    dataset_min: 100
  calibration:
    data_points_min: 100

scope:
  golden_dir: tests/fixtures/golden/
  rag_eval_dir: tests/fixtures/rag_eval/
  routing_dataset: tests/fixtures/routing/labeled_requests.jsonl
  eval_script: scripts/evaluate_extractions.py
  personality_files: []                    # Paths to AI behaviour configuration files
  vector_store_url: "http://localhost:6333"
```

---

## Run History

| Run | Date | Trigger | Report |
|-----|------|---------|--------|
| AI1 | _pending_ | Initial baseline | — |

## License

Part of [qual-gate](https://github.com/Nelvradia/qual-gate). Licensed under [Apache 2.0](../../LICENSE).
