#!/usr/bin/env bash
# glossary-linter.sh — Detect bare ambiguous terms per G01 glossary
#
# Scans Rust source files for bare usage of overloaded terms that should
# always be qualified. Returns non-zero if violations are found.
#
# Usage:
#   ./quality/instruments/glossary-linter.sh [--strict] [path...]
#
# Flags:
#   --strict   Exit 1 on any violation (default: advisory, exit 0)
#
# Default paths: core/core/daemon/src core/core/enforcer/src

set -euo pipefail

STRICT=0
PATHS=()

while [[ $# -gt 0 ]]; do
    case "$1" in
        --strict) STRICT=1; shift ;;
        *) PATHS+=("$1"); shift ;;
    esac
done

if [[ ${#PATHS[@]} -eq 0 ]]; then
    PATHS=(core/core/daemon/src core/core/enforcer/src)
fi

ALLOWLIST_FILE="quality/instruments/glossary-allowlist.txt"

# ---------------------------------------------------------------------------
# Bare term patterns from G01
# Each entry: TERM | GREP_PATTERN | QUALIFIED_ALTERNATIVES
# ---------------------------------------------------------------------------
# We search for the bare word used as an identifier (variable, field, param)
# but not as part of a qualified form or in comments/strings.

declare -A TERMS
TERMS=(
    ["domain"]='(?<![a-z_])domain(?![a-z_])'
    ["context"]='(?<![a-z_])context(?![a-z_])'
    ["trigger"]='(?<![a-z_])trigger(?![a-z_])'
    ["session"]='(?<![a-z_])session(?![a-z_])'
    ["template"]='(?<![a-z_])template(?![a-z_])'
    ["thread"]='(?<![a-z_])thread(?![a-z_])'
)

# Qualified forms that are OK (these patterns suppress false positives)
QUALIFIED_OK='enforcer_domain|life_domain|adapter_domain|domain:|conversation_context|life_context|code_context|conversation_mode|proactive_trigger|workflow_trigger|conversation_session|time_session|timer_session|thread_id|thread_summary|template_id|template_name|template_category|ToolDefinition|FunctionDefinition'

# Additional allowlist patterns (common Rust/framework uses that aren't G01 violations)
FRAMEWORK_OK='std::thread|tokio::task|async_trait|#\[cfg|//|///|/\*|domain\(\)|\.domain|test_|_test|mod tests|pub struct|pub enum|pub fn|impl |use |domain_label|sub_domain|domain_key|\.context\(|anyhow::Context|context!|context_window|ContextBudget|context_budget|estimate_tokens|ContextManager|template_id|template_name|template_category|trigger_name|trigger_id|session_id|thread_id|fn domain|_domain|domain_'

TOTAL_VIOLATIONS=0
VIOLATION_FILES=0

for dir in "${PATHS[@]}"; do
    if [[ ! -d "$dir" ]]; then
        echo "WARN: directory $dir not found, skipping" >&2
        continue
    fi

    for term in "${!TERMS[@]}"; do
        pattern="${TERMS[$term]}"

        # Use ripgrep if available, fall back to grep
        if command -v rg &>/dev/null; then
            matches=$(rg -n -P "$pattern" --type rust "$dir" 2>/dev/null || true)
        else
            matches=$(grep -rnP "$pattern" --include='*.rs' "$dir" 2>/dev/null || true)
        fi

        # Filter out qualified forms, framework usage, and test code
        filtered=$(echo "$matches" \
            | grep -vP "$QUALIFIED_OK" 2>/dev/null \
            | grep -vP "$FRAMEWORK_OK" 2>/dev/null \
            | grep -vP '#\[cfg\(test\)\]' 2>/dev/null \
            || true)

        # Filter out allowlisted lines if allowlist file exists
        if [[ -f "$ALLOWLIST_FILE" ]]; then
            while IFS= read -r allow_pattern; do
                [[ -z "$allow_pattern" || "$allow_pattern" == \#* ]] && continue
                filtered=$(echo "$filtered" | grep -v "$allow_pattern" 2>/dev/null || true)
            done < "$ALLOWLIST_FILE"
        fi

        # Remove empty lines
        filtered=$(echo "$filtered" | sed '/^$/d')

        if [[ -n "$filtered" ]]; then
            count=$(echo "$filtered" | wc -l)
            TOTAL_VIOLATIONS=$((TOTAL_VIOLATIONS + count))
            echo ""
            echo "=== Bare '$term' ($count occurrences) ==="
            echo "$filtered" | head -20
            if [[ $count -gt 20 ]]; then
                echo "  ... and $((count - 20)) more"
            fi
        fi
    done
done

echo ""
echo "--- Glossary Lint Summary ---"
echo "Total bare-term violations: $TOTAL_VIOLATIONS"

if [[ $TOTAL_VIOLATIONS -gt 0 ]]; then
    echo "Qualify bare terms per docs/four-pillars/gaps/G01-glossary.md"
    if [[ $STRICT -eq 1 ]]; then
        exit 1
    fi
fi

exit 0
