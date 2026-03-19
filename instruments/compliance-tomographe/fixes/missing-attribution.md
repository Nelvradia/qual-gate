---
title: "Fix: Missing Attribution"
status: current
last-updated: 2026-03-19
instrument: compliance-tomographe
severity-range: "Major"
---

# Fix: Missing Attribution

## What this means

Your project uses third-party libraries or code that require attribution under their licence
terms, but the required notices are missing or incomplete. Most permissive licences (MIT,
Apache-2.0, BSD) require that the copyright notice and licence text be included in
redistributions. Failing to provide attribution is a licence violation regardless of how
permissive the licence appears. For Apache-2.0 specifically, a NOTICE file is required if the
upstream project includes one.

## How to fix

### Step 1: Generate a complete dependency inventory

### Python

```python
# Generate a comprehensive attribution report
pip install pip-licenses

# Full attribution with licence text
pip-licenses --format=plain-vertical \
    --with-license-file \
    --no-license-path \
    --output-file=THIRD_PARTY_NOTICES.txt

# Markdown format for documentation
pip-licenses --format=markdown \
    --with-license-file \
    --with-authors \
    --with-urls \
    --output-file=ATTRIBUTIONS.md

# Verify no packages have unknown licences
pip-licenses --allow-only="MIT;Apache-2.0;BSD-2-Clause;BSD-3-Clause;ISC;PSF-2.0"
```

### Rust

```bash
# cargo-about generates attribution documents
cargo install cargo-about

# Create a configuration file
cat > about.toml << 'EOF'
accepted = [
    "MIT",
    "Apache-2.0",
    "BSD-2-Clause",
    "BSD-3-Clause",
    "ISC",
    "Zlib",
]
EOF

# Generate attribution in HTML or text
cargo about generate about.hbs > ATTRIBUTIONS.html

# Simpler: cargo-license for a quick list
cargo license --authors --do-not-bundle > THIRD_PARTY_NOTICES.txt
```

### TypeScript

```bash
# Generate a comprehensive NOTICE file
npx license-checker --csv --out third-party-licences.csv

# Generate with full licence text
npx license-checker --customPath customFormat.json --out ATTRIBUTIONS.md

# For production dependencies only
npx generate-license-file --input package.json --output THIRD_PARTY_NOTICES.txt
npm install -g generate-license-file
generate-license-file --input package.json --output THIRD_PARTY_NOTICES.txt
```

### Go

```bash
# Google's go-licenses tool extracts and saves licence files
go install github.com/google/go-licenses@latest

# Save all licence files into a directory
go-licenses save ./... --save_path=third_party/licences

# Generate a CSV report
go-licenses csv ./... > third-party-licences.csv

# Report any libraries with missing licence info
go-licenses check ./... 2>&1 | grep -i "unknown"
```

### General

### Step 2: Create a NOTICE file

The NOTICE file sits at your project root and aggregates all required attributions.

```text
This product includes software developed by third parties.

================================================================================
Library: requests
Version: 2.31.0
Licence: Apache-2.0
Copyright: Copyright 2019 Kenneth Reitz
URL: https://github.com/psf/requests

Licensed under the Apache License, Version 2.0. You may obtain a copy at:
http://www.apache.org/licenses/LICENSE-2.0
================================================================================

Library: serde
Version: 1.0.197
Licence: MIT OR Apache-2.0
Copyright: Copyright (c) 2014 The Rust Project Developers
URL: https://github.com/serde-rs/serde
================================================================================
```

### Step 3: Maintain attribution in distributed artefacts

Attribution must travel with the software, not just live in the source repo:

- **Docker images**: Copy `NOTICE` and `THIRD_PARTY_NOTICES.txt` into the image. Place them in
  `/usr/share/doc/<project>/` or a similar standard location.
- **Binary distributions**: Bundle the NOTICE file alongside the executable.
- **Web applications**: Include an "Open Source Licences" page or endpoint.
- **Libraries**: Include the NOTICE file in the published package.

```dockerfile
# Example: include attribution in Docker image
COPY NOTICE /usr/share/doc/myproject/NOTICE
COPY THIRD_PARTY_NOTICES.txt /usr/share/doc/myproject/THIRD_PARTY_NOTICES.txt
```

### Step 4: Handle Apache-2.0 NOTICE file requirements

Apache-2.0 has a specific requirement: if an upstream dependency ships a NOTICE file, you must
include its contents in your own NOTICE. Check each Apache-2.0 dependency for a NOTICE file:

```bash
# Python: check site-packages for NOTICE files
find $(python -c "import site; print(site.getsitepackages()[0])") \
    -name "NOTICE*" -type f 2>/dev/null

# Rust: check cargo registry
find ~/.cargo/registry/src -name "NOTICE*" -type f 2>/dev/null

# Node: check node_modules
find node_modules -maxdepth 2 -name "NOTICE*" -type f 2>/dev/null
```

## Prevention

**CI-enforceable checks:**

```yaml
# GitLab CI example
attribution-check:
  stage: lint
  script:
    # Verify NOTICE file exists
    - test -f NOTICE || (echo "ERROR: NOTICE file missing" && exit 1)
    # Regenerate attribution and diff against committed version
    - pip-licenses --format=plain-vertical --with-license-file --no-license-path
        --output-file=/tmp/generated-notices.txt
    - diff -u THIRD_PARTY_NOTICES.txt /tmp/generated-notices.txt
        || (echo "ERROR: Attribution file is stale. Regenerate it." && exit 1)
  rules:
    - if: $CI_PIPELINE_SOURCE == "merge_request_event"
      changes:
        - "**/requirements*.txt"
        - "**/Cargo.toml"
        - "**/package.json"
        - "**/go.sum"
```

**Process:**

- Regenerate attribution files every time dependencies change. Automate this in CI.
- Review upstream NOTICE files when adding Apache-2.0 dependencies.
- Include attribution review as a checklist item in MR templates.
- For vendored code (copy-pasted from another project), add inline attribution comments at
  the top of the file with the original licence and copyright.
