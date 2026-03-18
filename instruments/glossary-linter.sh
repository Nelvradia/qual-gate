#!/usr/bin/env bash
# glossary-linter.sh — Detect bare ambiguous terms per G01 glossary
#
# Scans source files for bare usage of overloaded terms that should
# always be qualified. Returns non-zero in strict mode if violations found.
#
# Usage:
#   ./instruments/glossary-linter.sh [options] [path...]
#
# Options:
#   --strict          Exit 1 on any violation (default: advisory, exit 0)
#   --terms-file F    Load bare terms from YAML/text file (default: built-in terms)
#   --allowlist F     Path to allowlist file (default: instruments/glossary-allowlist.txt)
#   --type LANGS      Comma-separated language types for ripgrep (default: all)
#   --glossary-doc F  Doc reference for remediation output (default: none)
#
# Default paths: src/

set -euo pipefail

STRICT=0
PATHS=()
TERMS_FILE=""
ALLOWLIST_FILE="instruments/glossary-allowlist.txt"
TYPE_FLAG=""
GLOSSARY_DOC=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --strict) STRICT=1; shift ;;
        --terms-file)
            TERMS_FILE="$2"; shift 2 ;;
        --allowlist)
            ALLOWLIST_FILE="$2"; shift 2 ;;
        --type)
            TYPE_FLAG="$2"; shift 2 ;;
        --glossary-doc)
            GLOSSARY_DOC="$2"; shift 2 ;;
        --help|-h)
            sed -n '2,/^$/{ s/^# //; s/^#//; p }' "$0"
            exit 0 ;;
        *) PATHS+=("$1"); shift ;;
    esac
done

if [[ ${#PATHS[@]} -eq 0 ]]; then
    PATHS=(src/)
fi

# ---------------------------------------------------------------------------
# Build ripgrep type flags
# ---------------------------------------------------------------------------
RG_TYPE_ARGS=()
if [[ -n "$TYPE_FLAG" ]]; then
    IFS=',' read -ra LANGS <<< "$TYPE_FLAG"
    for lang in "${LANGS[@]}"; do
        RG_TYPE_ARGS+=(--type "$lang")
    done
fi
# When no --type given, scan all files (no type filter to ripgrep)

# ---------------------------------------------------------------------------
# Bare term patterns
# ---------------------------------------------------------------------------
# When --terms-file is given, load terms from the file (YAML format).
# Otherwise fall back to built-in terms for backward compatibility.

declare -A TERMS
declare -A TERMS_QUALIFIED_OK

if [[ -n "$TERMS_FILE" ]]; then
    # Parse YAML terms file: extract term name, pattern, and qualified_ok list.
    # Requires yq (https://github.com/mikefarah/yq).
    if ! command -v yq &>/dev/null; then
        echo "ERROR: --terms-file requires yq but it is not installed" >&2
        exit 2
    fi
    while IFS= read -r term; do
        pattern=$(yq ".terms.${term}.pattern" "$TERMS_FILE")
        TERMS["$term"]="$pattern"
        qualified=$(yq ".terms.${term}.qualified_ok | join(\"|\")" "$TERMS_FILE" 2>/dev/null || echo "")
        TERMS_QUALIFIED_OK["$term"]="$qualified"
    done < <(yq '.terms | keys | .[]' "$TERMS_FILE")
else
    # Built-in terms (backward compatible with original linter)
    TERMS=(
        ["domain"]='(?<![a-z_])domain(?![a-z_])'
        ["context"]='(?<![a-z_])context(?![a-z_])'
        ["trigger"]='(?<![a-z_])trigger(?![a-z_])'
        ["session"]='(?<![a-z_])session(?![a-z_])'
        ["template"]='(?<![a-z_])template(?![a-z_])'
        ["thread"]='(?<![a-z_])thread(?![a-z_])'
    )
fi

# Qualified forms that are OK (these patterns suppress false positives)
QUALIFIED_OK='domain:|conversation_context|life_context|code_context|conversation_mode|proactive_trigger|workflow_trigger|conversation_session|time_session|timer_session|thread_id|thread_summary|template_id|template_name|template_category|ToolDefinition|FunctionDefinition'

# Additional allowlist patterns (common framework uses that aren't G01 violations)
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
            matches=$(rg -n -P "$pattern" "${RG_TYPE_ARGS[@]}" "$dir" 2>/dev/null || true)
        else
            matches=$(grep -rnP "$pattern" "$dir" 2>/dev/null || true)
        fi

        # Build combined qualified-ok pattern for this term
        term_qualified="${QUALIFIED_OK}"
        if [[ -n "${TERMS_QUALIFIED_OK[$term]:-}" ]]; then
            term_qualified="${term_qualified}|${TERMS_QUALIFIED_OK[$term]}"
        fi

        # Filter out qualified forms, framework usage, and test code
        filtered=$(echo "$matches" \
            | grep -vP "$term_qualified" 2>/dev/null \
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
    if [[ -n "$GLOSSARY_DOC" ]]; then
        echo "Qualify bare terms per $GLOSSARY_DOC"
    else
        echo "Qualify bare terms per your project's glossary documentation."
    fi
    if [[ $STRICT -eq 1 ]]; then
        exit 1
    fi
fi

exit 0
