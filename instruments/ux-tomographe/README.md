# ux-tomographe

**User experience diagnostic instrument.** Scans interface code, interaction patterns, accessibility compliance, personality rendering, cross-platform consistency, and conversation quality. Produces a structured report with severity ratings and actionable recommendations.

**Covers DR Sections:** S11 (UX / Human Factors), feeds into Lens 4.1 (User Experience), 4.2 (Product Management), 4.3 (Accessibility & Multi-Modal)

**DR Integration:** This instrument is a **mandatory pre-DR stage** for any Design Review that includes UI-touching components. Its output populates DR Section S11 directly — the DR template references UX Tomographe findings, composite score, and drift delta rather than a manual checklist. See `docs/reviews/DR-PROCESS.md` §2b and §6 for execution triggers and verdict thresholds.

---

## Quick Start

```bash
# Full scan (all phases)
"Read instruments/ux-tomographe/README.md and execute a full UX scan."

# Targeted scan (single phase)
"Read instruments/ux-tomographe/README.md and execute Phase 3 (Accessibility) only."

# Delta scan
"Read instruments/ux-tomographe/README.md and execute a delta scan vs the last run."
```

---

## Scan Phases

| Phase | Name | What It Does | Requires Running App? |
|-------|------|-------------|----------------------|
| **1** | Component Inventory | Catalog all UI components, screens, and interaction surfaces | No |
| **2** | Interaction Patterns | Verify core user flows match design docs and handle edge cases | No (code analysis) |
| **3** | Accessibility | Audit for WCAG 2.1 AA compliance, semantic markup, touch targets | No (code analysis) |
| **4** | Personality & Tone | Verify personality system rendering, role switching, anti-trait compliance | Partial (needs sample outputs) |
| **5** | Conversation Quality | Assess response formatting, confidence signaling, error communication | Partial |
| **6** | Cross-Platform Consistency | Compare component parity and behavioral consistency across the project's target platforms | No |
| **7** | Progressive Disclosure | Verify information architecture follows depth-over-breadth strategy | No |
| **8** | Report | Compile findings into structured UX report | No |

---

## Phase 1 — Component Inventory

**Goal:** Build a complete map of every UI component, screen, and interaction surface across all target platforms.

### LLM steps

1. Discover what UI framework(s) are present by reading source files in `ui_source_dirs`: look for component definitions, widget patterns, view declarations, or JSX/TSX syntax.
2. Build an inventory of UI components: screens/pages, reusable components, navigation structure.
3. Note the framework(s) found — this informs which accelerator patterns are relevant in subsequent phases.

### Accelerator tools (optional)

```bash
# Android / Compose (if available)
# Find all Composable functions
grep -rn '@Composable' <android_src> --include='*.kt' | grep 'fun ' | \
  sed 's/.*fun \([A-Za-z]*\).*/\1/' | sort -u

# Find all screens/routes
grep -rn 'NavHost\|composable(\|navigation(' <android_src> --include='*.kt'

# Find all ViewModels
grep -rn 'class.*ViewModel' <android_src> --include='*.kt'

# Find all UI state classes
grep -rn 'data class.*State\|sealed.*UiState\|sealed.*Event' <android_src> --include='*.kt'

# Count composables by directory
find <android_src> -name '*.kt' -exec grep -l '@Composable' {} \; | \
  sed 's|/[^/]*$||' | sort | uniq -c | sort -rn
```

```bash
# React / Web (if available)
# Find all React components
grep -rn 'export.*function\|export default\|export const.*=' <web_src> \
  --include='*.tsx' --include='*.jsx' | grep -v 'test\|spec' | \
  sed 's/.*export[^:]*\(function\|const\|default\) \([A-Za-z]*\).*/\2/' | sort -u

# Find all route definitions
grep -rn 'Route\|path:' <web_src> --include='*.tsx' | head -20

# Find all hooks (custom state management)
grep -rn 'function use[A-Z]\|const use[A-Z]' <web_src>/hooks/ --include='*.ts'

# Count components by directory
find <web_src> -name '*.tsx' | sed 's|/[^/]*$||' | sort | uniq -c | sort -rn
```

### Output Schema

```json
{
  "timestamp": "ISO-8601",
  "platform_a": {
    "composables": [],
    "screens": [],
    "viewmodels": [],
    "state_classes": [],
    "total_composables": 0
  },
  "platform_b": {
    "components": [],
    "routes": [],
    "hooks": [],
    "total_components": 0
  },
  "shared_concepts": {
    "both_have": [],
    "platform_a_only": [],
    "platform_b_only": []
  }
}
```

---

## Phase 2 — Interaction Patterns

**Goal:** Verify that core user flows are correctly implemented and handle edge cases.

### Core Flows to Audit

| Flow | Platform A Files | Platform B Files | Design Doc |
|------|-----------------|-----------------|------------|
| **Onboarding** | _project-specific_ | _project-specific_ | _project-specific_ |
| **Chat / Main Interaction** | _project-specific_ | _project-specific_ | _project-specific_ |
| **Approval / Confirmation** | _project-specific_ | _project-specific_ | _project-specific_ |
| **Dashboard / Summary** | _project-specific_ | _project-specific_ | _project-specific_ |
| **Reconnection** | _project-specific_ | _project-specific_ | _project-specific_ |

### LLM steps

1. Read UI component source files for each flow listed above.
2. For each interactive element (buttons, forms, navigation, gestures): verify it has defined states — enabled, disabled, loading, error. This is universal regardless of framework.
3. Verify that async operations (network requests, file loading) show a loading state and handle errors visibly. A user must never see a blank, frozen, or silently failed UI.
4. Look for hardcoded delays or animations with no respect for system accessibility settings (reduced motion, etc.).

### Accelerator tools (optional)

```bash
# All platforms — search for state-handling patterns in the relevant source dirs
# Adapt file extensions to the framework found in Phase 1

# Error states
grep -n 'error\|Error\|catch\|onError\|onFailure' <file> | head -20
# Check: Are errors shown to the user? Are they actionable?

# Loading states
grep -n 'loading\|Loading\|isLoading\|progress\|Progress' <file>
# Check: Is there feedback while waiting? Spinner? Skeleton?

# Empty states
grep -n 'empty\|Empty\|no.*data\|no.*message' <file>
# Check: What shows when there's no data? Is it helpful?

# Offline handling
grep -n 'offline\|Offline\|disconnect\|connectionState' <file>
# Check: Does the UI degrade gracefully when offline?
```

```bash
# Android / Kotlin — state pattern examples
grep -rn 'isLoading\|UiState\|onFailure' <android_src> --include='*.kt'
```

```bash
# React / Web — state pattern examples
grep -rn 'useState\|isLoading\|onError' <web_src> --include='*.tsx' --include='*.ts'
```

### Severity Rules

| Finding | Severity |
|---------|----------|
| Core flow has no error handling (crashes on failure) | **Major** |
| No loading state (user sees blank screen while waiting) | **Minor** |
| No empty state (blank screen when no data) | **Minor** |
| No offline handling (app freezes or crashes) | **Major** |
| Onboarding flow doesn't validate input | **Major** |
| Security verification silently ignored | **Major** |
| Reconnection can permanently fail | **Major** |

---

## Phase 3 — Accessibility

**Goal:** Audit for WCAG 2.1 AA compliance across all target platforms.

### LLM steps

1. Read all UI component files identified in Phase 1.
2. For each interactive element: verify a semantic accessibility label is present. The mechanism varies by platform but the requirement is universal:
   - HTML/React: `aria-label`, `aria-labelledby`, semantic elements (`<button>`, `<input>`, `<nav>`)
   - Android/Compose: `contentDescription`, `semantics { }` modifier
   - SwiftUI: `.accessibilityLabel()`, `.accessibilityHint()`
   - Flutter: `Semantics` widget
3. Check that touch/click targets meet minimum size requirements (44×44pt / 48×48dp is the universal guideline).
4. Check that text content uses relative sizing (rem/em/sp/dp) not fixed pixels where possible.
5. Check that colour contrast is not the only visual differentiator for state or meaning.

### Accelerator tools (optional)

```bash
# Android / Compose (if available)
# Content descriptions on interactive elements
grep -rn 'contentDescription\|semantics {' <android_src> --include='*.kt' | wc -l
# vs total interactive elements:
grep -rn 'clickable\|onClick\|Button\|IconButton' <android_src> --include='*.kt' | wc -l
# Ratio should be close to 1:1

# Touch target sizes (minimum 48dp per Material 3)
grep -rn 'size.*dp\|Modifier\.size\|\.padding' <android_src> --include='*.kt' | \
  grep -E '[0-9]+\.dp' | awk -F'[^0-9]' '{for(i=1;i<=NF;i++) if($i+0 < 48 && $i+0 > 0) print NR": "$i"dp — possible undersized target"}'

# Color contrast (static analysis — check for hardcoded colors)
grep -rn 'Color(0x\|Color(\.' <android_src> --include='*.kt' | head -20
# Material 3 theme colors generally pass contrast — custom colors need verification

# Text scaling support
grep -rn 'sp\|TextUnit' <android_src> --include='*.kt' | grep -v 'dp' | head -10
# Text should use sp (scales with system font size), not dp

# Screen reader traversal order
grep -rn 'traversalIndex\|semantics.*heading\|clearAndSetSemantics' <android_src> --include='*.kt'
```

```bash
# React / Web (if available)
# ARIA labels and roles
grep -rn 'aria-label\|aria-role\|role=' <web_src> --include='*.tsx' | wc -l
# vs total interactive elements:
grep -rn 'onClick\|onKeyDown\|<button\|<a ' <web_src> --include='*.tsx' | wc -l

# Alt text on images
grep -rn '<img' <web_src> --include='*.tsx' | grep -v 'alt='

# Keyboard navigation
grep -rn 'onKeyDown\|onKeyUp\|tabIndex\|focus\|autoFocus' <web_src> --include='*.tsx' | wc -l

# Focus management (modal dialogs should trap focus)
grep -rn 'FocusTrap\|focus.*trap\|createFocusTrap' <web_src> --include='*.tsx'

# Color contrast (check for hardcoded colors vs CSS variables)
grep -rn 'color:\|background:\|border-color:' <web_src> --include='*.css' --include='*.tsx' | \
  grep '#\|rgb\|hsl' | grep -v 'var(--' | head -20
# Hardcoded colors need contrast verification

# Reduced motion support
grep -rn 'prefers-reduced-motion\|reduceMotion' <web_src> --include='*.css' --include='*.tsx'
```

### Checklist

**Perceivable:**
- [ ] All interactive elements have text labels (content descriptions / aria-labels)
- [ ] Images have alt text or are marked decorative
- [ ] Color is not the sole means of conveying information
- [ ] Text contrast ratio >= 4.5:1 (AA), >= 7:1 (AAA — recommended)
- [ ] Text uses scalable units (sp on Android, rem/em on web)

**Operable:**
- [ ] All functionality reachable via keyboard (Desktop)
- [ ] Touch targets >= 48dp (Android) / 44px (Web)
- [ ] Focus visible and logical traversal order
- [ ] No time limits without user control
- [ ] Reduced motion respected

**Understandable:**
- [ ] Error messages are descriptive and suggest corrections
- [ ] Form inputs have visible labels
- [ ] Navigation is consistent across screens
- [ ] Language is declared (`lang` attribute)

**Robust:**
- [ ] Semantic HTML/Compose (headings, lists, landmarks)
- [ ] Valid markup / component structure
- [ ] Compatible with assistive technologies (TalkBack / screen readers)

### Severity Rules

| Finding | Severity |
|---------|----------|
| Interactive element with no accessible label | **Minor** (internal use), **Major** (public-facing) |
| Touch target <48dp / click target <44px | **Minor** |
| Image with no alt text | **Observation** |
| No keyboard navigation on Desktop | **Minor** (internal), **Major** (public-facing) |
| Color-only information | **Minor** |
| No focus management in modals | **Minor** |

---

## Phase 4 — Personality & Tone

**Goal:** Verify the AI personality system renders correctly across contexts and roles.

### LLM steps

1. Read all user-visible strings, labels, button text, and error messages found in `ui_source_dirs` and `personality_files`.
2. Assess tone consistency: formal vs casual, active vs passive, concise vs verbose. Flag inconsistencies between screens or components.
3. Check for error messages that expose technical internals to users (stack traces, internal identifiers, raw exception text).
4. If a personality spec or design guidelines file exists in config `personality_files`, compare the rendered strings against it.

### Accelerator tools (optional)

```bash
# AI behaviour configuration files
find . -name '*.md' -path '*/personality/*' -o -name '*system-prompt*' 2>/dev/null

# Role definitions in code — adapt extensions to the framework found in Phase 1
grep -rn 'role\|Role\|personality\|persona' \
  src/ --include='*.rs' --include='*.py' --include='*.ts' | head -20

# Anti-trait enforcement
grep -rn 'sycophant\|patroni\|never.*say\|forbidden.*phrase\|anti_trait' \
  src/ config/ --include='*.rs' --include='*.py' --include='*.yaml'

# Confidence signaling
grep -rn 'confidence\|Confidence\|certainty\|unsure\|I.m not sure\|I believe' \
  src/ --include='*.rs' --include='*.py' | head -20

# Signature phrases
grep -rn 'signature\|catchphrase' src/ config/ --include='*.rs' --include='*.py' --include='*.yaml'

# Android / Compose — string literals in UI
grep -rn 'stringResource\|text = "' <android_src> --include='*.kt' | head -30

# React / Web — string literals in UI
grep -rn 'children\|label\|placeholder\|aria-label' <web_src> --include='*.tsx' | head -30
```

### Personality Evaluation Checklist

- [ ] Roles defined and distinguishable
- [ ] Role selection is context-dependent
- [ ] Anti-traits enforced (never sycophantic, never patronizing, never panicked)
- [ ] Confidence signaling implemented (e.g. high/moderate/low/uncertain)
- [ ] Error communication distinguishes "I don't know" from "something broke"
- [ ] Response length adapts to context (structured vs natural)
- [ ] AI bubble renders consistently on all target platforms
- [ ] Attention levels visual (if applicable)

---

## Phase 5 — Conversation Quality

**Goal:** Assess the quality of AI-generated responses as rendered in the UI.

### LLM steps

1. Identify components responsible for rendering formatted content (markdown, code, rich text) across all platforms found in Phase 1.
2. Check that code blocks use monospace fonts and syntax highlighting where appropriate.
3. Check that long content is not truncated without user control (scroll, expand, pagination).
4. Check that content rendering is consistent across platforms (if multiple platforms exist).

### Accelerator tools (optional)

```bash
# All platforms — adapt extensions to the framework found in Phase 1

# Markdown rendering
grep -rn 'markdown\|Markdown\|renderMarkdown\|MarkdownText' \
  <ui_source_dirs> --include='*.kt' --include='*.tsx'
# Check: Does the UI render markdown correctly? Bold, code blocks, lists, links?

# Code block rendering
grep -rn 'code.*block\|syntax.*highlight\|CodeBlock\|pre>' \
  <ui_source_dirs> --include='*.kt' --include='*.tsx'

# Structured response rendering (tables, summaries, cards)
grep -rn 'Table\|StructuredView\|CardView\|SummaryCard' \
  <ui_source_dirs> --include='*.kt' --include='*.tsx'

# Typing indicator / streaming
grep -rn 'typing\|streaming\|isTyping\|StreamingText\|chunk' \
  <ui_source_dirs> --include='*.kt' --include='*.tsx'

# Message timestamp display
grep -rn 'timestamp\|timeAgo\|DateFormat\|formatDate\|relative.*time' \
  <ui_source_dirs> --include='*.kt' --include='*.tsx'

# Thread / conversation management
grep -rn 'thread\|Thread\|conversation.*id\|ConversationList' \
  <ui_source_dirs> --include='*.kt' --include='*.tsx'
```

### Checklist

- [ ] Markdown renders correctly (bold, italic, code, links, lists, headings)
- [ ] Code blocks have syntax highlighting
- [ ] Long messages scroll properly (no overflow, no truncation)
- [ ] Streaming/typing indicator shows during LLM generation
- [ ] Timestamps are human-readable (relative: "2 min ago")
- [ ] Thread management exists (multiple conversation threads)
- [ ] Structured responses have dedicated rendering
- [ ] Approval/confirmation cards render inline with correct action buttons
- [ ] Error messages are user-friendly (not raw stack traces)

---

## Phase 6 — Cross-Platform Consistency

**Goal:** Verify all target platforms present the same information and interactions.

### LLM steps

1. If multiple UI platforms are present (mobile + desktop, web + native, etc.), identify the feature set of each using the inventory from Phase 1.
2. Compare feature parity: are core user flows available on all platforms?
3. Check that platform-specific affordances are used correctly (bottom navigation on mobile, menu bar on desktop) rather than slavishly copying one platform's patterns to another.

### Accelerator tools (optional)

```bash
# Android / Compose — build component list (if available)
PLATFORM_A_COMPONENTS=$(grep -rn '@Composable' <android_src> --include='*.kt' | \
  grep 'fun ' | sed 's/.*fun \([A-Za-z]*\).*/\1/' | sort -u)

# React / Web — build component list (if available)
PLATFORM_B_COMPONENTS=$(grep -rn 'export' <web_src> --include='*.tsx' | \
  grep -v 'test\|spec\|type\|interface' | \
  sed 's/.*export[^:]*\(function\|const\|default\) \([A-Za-z]*\).*/\2/' | sort -u)

# Compare (manual review of output needed)
echo "=== Platform A only ==="
comm -23 <(echo "$PLATFORM_A_COMPONENTS") <(echo "$PLATFORM_B_COMPONENTS")
echo "=== Platform B only ==="
comm -13 <(echo "$PLATFORM_A_COMPONENTS") <(echo "$PLATFORM_B_COMPONENTS")
echo "=== Both ==="
comm -12 <(echo "$PLATFORM_A_COMPONENTS") <(echo "$PLATFORM_B_COMPONENTS")
```

### Behavioral Consistency

| Behavior | Platform A | Platform B | Must Match? |
|----------|-----------|-----------|-------------|
| Onboarding flow | _project-specific_ | _project-specific_ | Yes (UX, not mechanics) |
| Primary interaction | _project-specific_ | _project-specific_ | Yes |
| Approval flow | _project-specific_ | _project-specific_ | Partial (biometric is platform-specific) |
| Notifications | _project-specific_ | _project-specific_ | Different mechanism, same content |
| Offline indicator | Banner + queue | Banner + queue | Yes |
| Dashboard layout | _project-specific_ | _project-specific_ | Different layout, same data |
| Command palette | N/A (mobile uses voice/tap) | Keyboard shortcut | Platform-specific (OK to differ) |

### Severity Rules

| Finding | Severity |
|---------|----------|
| Core concept missing on one platform | **Major** |
| Same data displayed differently without good reason | **Minor** |
| Platform-appropriate adaptation (e.g., bottom nav vs sidebar) | **OK** |
| Feature exists on one platform only but is platform-specific (e.g., biometric) | **OK** |

---

## Phase 7 — Progressive Disclosure

**Goal:** Verify the information architecture follows a "depth over breadth" strategy.

### LLM steps

1. Read navigation and screen/page source files identified in Phase 1.
2. Identify whether complex features are hidden behind progressive disclosure (expandable sections, detail views, advanced settings panels).
3. Verify primary actions are prominent and secondary actions are accessible but not cluttering the primary interface.
4. Check that destructive actions (delete, reset) require confirmation and are not placed near common actions.

### Accelerator tools (optional)

```bash
# All platforms — adapt extensions to the framework found in Phase 1

# Check for expandable/collapsible sections
grep -rn 'expand\|collapse\|Accordion\|Expandable\|AnimatedVisibility\|showMore' \
  <ui_source_dirs> --include='*.kt' --include='*.tsx'

# Check for detail views (tap to see more)
grep -rn 'NavigateTo\|onClick.*navigate\|detail\|Detail' \
  <ui_source_dirs> --include='*.kt' --include='*.tsx'

# Check for workspace-distinct layouts (not one-size-fits-all)
grep -rn 'workspace\|Workspace\|layout.*type\|viewMode' \
  <ui_source_dirs> --include='*.kt' --include='*.tsx'

# Information hierarchy (headings, sections, nested content)
grep -rn 'h1\|h2\|h3\|Section\|SectionHeader\|Heading' \
  <ui_source_dirs> --include='*.kt' --include='*.tsx'
```

### Checklist

- [ ] Summaries show overview first, expandable sections for detail
- [ ] Chat messages don't overwhelm with data (structured views for complex responses)
- [ ] Dashboard (if exists) shows key metrics, links to detail views
- [ ] Notifications are triaged by attention level
- [ ] Settings/preferences are organized by category, not a flat list
- [ ] Help/onboarding is progressive (not a wall of text)
- [ ] Error detail is available but not shown by default (expand for stack trace / technical info)

---

## Phase 8 — Report

Compile all phase outputs into `output/YYYY-MM-DD_{project_name}/UX{n}-ux-tomographe.md` (see `qualitoscope/config.yaml` for `project_name`).

Include:
- Component inventory with gap analysis
- Interaction flow health summary
- Accessibility score and violations
- Personality rendering assessment
- Cross-platform consistency matrix
- Progressive disclosure evaluation
- Prioritized recommendations

---

## Directory Structure

```
instruments/ux-tomographe/
├── README.md
├── config.yaml
├── methods/
│   ├── 01-component-inventory.md
│   ├── 02-interaction-patterns.md
│   ├── 03-accessibility.md
│   ├── 04-personality-tone.md
│   ├── 05-conversation-quality.md
│   ├── 06-cross-platform.md
│   ├── 07-progressive-disclosure.md
│   └── 08-report.md
├── checklists/
│   ├── accessibility-wcag.md           # Full WCAG 2.1 AA checklist
│   ├── personality-compliance.md       # Anti-traits, role verification
│   ├── cross-platform-parity.md        # Component and behavior parity
│   └── conversation-rendering.md       # Markdown, code blocks, structured views
├── templates/
│   └── report-template.md
└── fixes/
    └── README.md
```

---

## Configuration

This instrument reads project-specific paths from `project-profile.yaml` in the target project root. If a profile field is absent, the default from the profile schema applies. Instrument-specific thresholds remain in this instrument's `config.yaml`.

```yaml
thresholds:
  accessibility:
    min_labeled_interactive_ratio: 0.90    # 90% of interactive elements must have labels
    min_touch_target_dp: 48                # Android Material 3 minimum
    min_click_target_px: 44                # Web minimum
    min_contrast_ratio: 4.5                # WCAG 2.1 AA
    enhanced_contrast_ratio: 7.0           # WCAG 2.1 AAA (target for public-facing)

  consistency:
    max_platform_a_only_concepts: 3        # Platform-specific features allowed
    max_platform_b_only_concepts: 3
    core_features_parity: 100              # Core flows must be on all platforms

  interaction:
    required_states: [loading, error, empty, offline]  # Every screen must handle these
    required_flows: []                     # Define per project

  personality:
    roles_defined: 0                       # Define per project
    anti_traits_enforced: true
    confidence_tiers: 4

scope:
  # ui_source_dirs: paths containing UI component source files — the LLM detects the framework
  ui_source_dirs: []
  personality_files: []                    # Paths to AI behaviour configuration files
  ux_spec: ""                              # Path to UX specification document
  design_docs: []                          # Paths to design documents

delta:
  # output goes to output/YYYY-MM-DD_{project_name}/ — see qualitoscope/config.yaml
  keep_runs: 10
```

---

## Severity & Verdict

| Verdict | Rule |
|---------|------|
| **PASS** | 0 Critical, 0 Major |
| **CONDITIONAL** | 0 Critical, <=2 Major |
| **FAIL** | >=1 Critical, OR >2 Major |

**Note:** Severity thresholds shift for public-facing releases: what's Minor for internal use becomes Major for customer-facing UX. Update the config accordingly when targeting external users.

---

## Run History

| Run | Date | Trigger | Findings | Report |
|-----|------|---------|----------|--------|
| UX1 | _pending_ | Initial baseline | — | — |

## License

Part of [qual-gate](https://github.com/Nelvradia/qual-gate). Licensed under [Apache 2.0](../../LICENSE).
