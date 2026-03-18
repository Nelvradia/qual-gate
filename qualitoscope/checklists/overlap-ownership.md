# Overlap Ownership Rules

Defines which instrument is authoritative when multiple instruments check the same concern. Used by Phase 3 (Overlap Resolution) to deduplicate findings.

## Ownership Table

### Privacy Tiers (P0-P3)
- **Primary:** `data-tomographe`
- **Secondary:** `compliance-tomographe`
- **Rule:** `data` owns classification checking ("column X is P2"). `compliance` owns GDPR policy compliance ("P2 data has retention policy"). Deduplicate classification findings — keep `data`'s version.
- **Fingerprint pattern:** `*privacy*`, `*P0*`, `*P1*`, `*P2*`, `*P3*`, `*data_classification*`

### Enforcer K1
- **Primary:** `compliance-tomographe`
- **Secondary:** `security-tomographe`
- **Rule:** `compliance` owns config completeness (all domains registered, metrics defined). `security` owns access control correctness (does the enforcer actually block?). Findings about *missing entries* → `compliance`. Findings about *bypass* → `security`.
- **Fingerprint pattern:** `*enforcer*`, `*K1*`, `*domain_count*`, `*action_coverage*`

### Supply Chain / Dependencies
- **Primary (CVEs, advisories):** `security-tomographe`
- **Primary (SBOM, unused deps, health, pinning):** `dependency-tomographe`
- **Secondary:** `code-tomographe`
- **Rule:** `security` owns CVE severity and vulnerability triage. `dependency` owns SBOM completeness, unused dep detection, dep health assessment, version pinning, and licence-tier classification. `code` owns dependency bloat and toolchain currency. If security and dependency both flag the same CVE, keep `security`'s severity. If dependency and code both flag the same dep as unhealthy, keep `dependency`'s version.
- **Fingerprint pattern:** `*cargo-audit*`, `*cargo-deny*`, `*cve*`, `*advisory*`, `*dependency*`, `*unused_dep*`, `*sbom*`, `*lockfile*`, `*pinning*`

### Licence Classification
- **Primary:** `dependency-tomographe`
- **Secondary:** `compliance-tomographe`
- **Rule:** `dependency` owns per-dep licence identification and tier classification (copyleft, restricted, permissive). `compliance` owns policy-level licence decisions (acceptable risk, export control). If both flag the same dep's licence, keep `dependency`'s classification and `compliance`'s policy verdict.
- **Fingerprint pattern:** `*licence*`, `*license*`, `*copyleft*`, `*gpl*`, `*agpl*`, `*attribution*`, `*notice*`

### Health Endpoints
- **Primary:** `observability-tomographe`
- **Secondary:** `performance-tomographe`
- **Rule:** `observability` owns endpoint existence and correctness. `performance` owns response time and resource cost. Deduplicate existence checks — keep `observability`'s version.
- **Fingerprint pattern:** `*/health*`, `*health_check*`, `*health_endpoint*`

### VERSION Files
- **Primary (release):** `deployment-tomographe`
- **Primary (docs):** `documentation-tomographe`
- **Rule:** `deployment` owns release process (tag matches VERSION). `documentation` owns cross-doc coherence (VERSION matches docs). Different aspects of same artifact — both findings kept, tagged with owner.
- **Fingerprint pattern:** `*VERSION*`, `*semver*`, `*version_file*`

### AI Personality Configuration
- **Primary (consistency):** `ux-tomographe`
- **Primary (quality):** `ai-ml-tomographe`
- **Primary (security):** `security-tomographe`
- **Rule:** Three distinct aspects — UX owns personality consistency, AI/ML owns prompt quality, security owns manipulation resistance. All findings kept, tagged with owner.
- **Fingerprint pattern:** `*SOUL*`, `*personality*`, `*prompt*voice*`

### Prompt Injection
- **Primary:** `security-tomographe`
- **Secondary:** `ai-ml-tomographe`
- **Rule:** `security` owns attack detection and defense verification. `ai-ml` owns quality degradation measurement. If both flag the same issue, merge into single finding with `security`'s severity.
- **Fingerprint pattern:** `*injection*`, `*sanitiz*`, `*adversarial*`

### Audit Trail
- **Primary (completeness):** `observability-tomographe`
- **Primary (correctness):** `security-tomographe`
- **Rule:** `observability` owns log completeness (are all events logged?). `security` owns access logging correctness (are the right events logged with the right detail?). Different aspects — both kept, tagged.
- **Fingerprint pattern:** `*audit*`, `*audit_log*`, `*access_log*`

## Resolution Process

1. Load all findings from all instruments
2. Compute fingerprint for each finding: `{file}:{check_type}:{location}`
3. Group findings with matching fingerprints
4. For each group with >1 finding:
   a. Match to an overlap area above using fingerprint patterns
   b. If match found: apply the ownership rule (keep primary, discard secondary)
   c. If no match: flag as new overlap needing ownership rule (severity: Minor)
5. If primary and secondary disagree on severity: flag for human review (severity: Observation)
6. Single-instrument findings pass through unchanged
