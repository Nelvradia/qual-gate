---
title: "Fix: Accessibility Violations"
status: current
last-updated: 2026-03-19
instrument: ux-tomographe
severity-range: "Major--Critical"
---

# Fix: Accessibility Violations

## What this means

Your application fails to meet WCAG 2.1 accessibility requirements. This includes missing or
incorrect ARIA attributes, insufficient colour contrast, absent alt text on images, broken keyboard
navigation, or inaccessible form controls. Accessibility violations exclude users who rely on
assistive technology (screen readers, switch devices, voice control) and expose your organisation
to legal risk under ADA, EAA, and similar legislation. Critical findings indicate that core
functionality is completely inaccessible to some users; Major findings indicate degraded but
partially functional access.

## How to fix

### TypeScript / React

**Install and configure `eslint-plugin-jsx-a11y`:**

```bash
npm install --save-dev eslint-plugin-jsx-a11y
```

```js
// eslint.config.js (flat config, ESLint 9+)
import jsxA11y from "eslint-plugin-jsx-a11y";

export default [
  jsxA11y.flatConfigs.recommended,
  {
    rules: {
      "jsx-a11y/alt-text": "error",
      "jsx-a11y/anchor-is-valid": "error",
      "jsx-a11y/click-events-have-key-events": "error",
      "jsx-a11y/no-noninteractive-element-interactions": "error",
      "jsx-a11y/label-has-associated-control": "error",
    },
  },
];
```

**Runtime accessibility auditing with `@axe-core/react`:**

```tsx
// src/index.tsx — development only
if (process.env.NODE_ENV === "development") {
  import("@axe-core/react").then((axe) => {
    axe.default(React, ReactDOM, 1000);
    // Violations appear in browser console with fix suggestions
  });
}
```

**Common violations and fixes:**

```tsx
// BAD: image without alt text
<img src="/hero.png" />

// GOOD: descriptive alt text (or empty alt for decorative images)
<img src="/hero.png" alt="Robot arm assembling a prosthetic hand" />
<img src="/decorative-divider.png" alt="" role="presentation" />

// BAD: click handler on non-interactive element without keyboard support
<div onClick={handleClick}>Click me</div>

// GOOD: use a button, or add keyboard + role
<button onClick={handleClick}>Click me</button>
// Alternative when button styling is undesirable:
<div
  role="button"
  tabIndex={0}
  onClick={handleClick}
  onKeyDown={(e) => {
    if (e.key === "Enter" || e.key === " ") handleClick();
  }}
>
  Click me
</div>

// BAD: form input without label
<input type="email" placeholder="Email" />

// GOOD: explicit label association
<label htmlFor="email-input">Email address</label>
<input id="email-input" type="email" placeholder="you@example.com" />

// BAD: colour-only error indication
<input style={{ borderColor: "red" }} />

// GOOD: colour + icon + text
<input aria-invalid="true" aria-describedby="email-error" />
<span id="email-error" role="alert">
  <ErrorIcon aria-hidden="true" /> Please enter a valid email address.
</span>

// BAD: modal traps focus or does not return focus on close
<div className="modal">{content}</div>

// GOOD: trap focus inside modal, restore on close
<dialog ref={dialogRef} aria-labelledby="modal-title">
  <h2 id="modal-title">Confirm action</h2>
  {content}
  <button onClick={close}>Close</button>
</dialog>
```

### TypeScript / Vue

**Use `eslint-plugin-vuejs-accessibility`:**

```bash
npm install --save-dev eslint-plugin-vuejs-accessibility
```

```vue
<!-- BAD: router-link without accessible text -->
<router-link :to="{ name: 'settings' }">
  <SettingsIcon />
</router-link>

<!-- GOOD: include screen-reader text -->
<router-link :to="{ name: 'settings' }" aria-label="Settings">
  <SettingsIcon aria-hidden="true" />
</router-link>
```

### TypeScript / Angular

**Use `@angular-eslint/template` accessibility rules:**

```bash
ng add @angular-eslint/schematics
```

```html
<!-- BAD: missing track for video -->
<video src="/demo.mp4" controls></video>

<!-- GOOD: include captions track -->
<video src="/demo.mp4" controls>
  <track kind="captions" src="/demo-captions.vtt" srclang="en" label="English" />
</video>
```

**Implement `LiveAnnouncer` for dynamic content:**

```typescript
import { LiveAnnouncer } from "@angular/cdk/a11y";

@Component({ /* ... */ })
export class SearchComponent {
  constructor(private announcer: LiveAnnouncer) {}

  onSearchComplete(count: number): void {
    this.announcer.announce(`${count} results found`);
  }
}
```

### General

**Automated scanning with axe-core in CI:**

```bash
# Install axe CLI
npm install -g @axe-core/cli

# Scan a running application
axe http://localhost:3000 --exit
# Exit code 1 if violations found
```

**Lighthouse accessibility audit:**

```bash
# Install lighthouse
npm install -g lighthouse

# Run accessibility audit (score threshold: 90)
lighthouse http://localhost:3000 \
  --only-categories=accessibility \
  --output=json \
  --output-path=./a11y-report.json

# Fail CI if score below threshold
node -e "
  const r = require('./a11y-report.json');
  const score = r.categories.accessibility.score * 100;
  console.log('Accessibility score:', score);
  if (score < 90) process.exit(1);
"
```

**Playwright accessibility testing:**

```typescript
import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

test("home page has no accessibility violations", async ({ page }) => {
  await page.goto("/");
  const results = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"])
    .analyze();
  expect(results.violations).toEqual([]);
});
```

**WCAG 2.1 checklist — most common violations:**

| Criterion | What to check |
|---|---|
| 1.1.1 Non-text content | Every `<img>` has `alt`; decorative images use `alt=""` |
| 1.3.1 Info and relationships | Headings are hierarchical; forms use `<label>` or `aria-label` |
| 1.4.3 Contrast (minimum) | Text has >= 4.5:1 contrast ratio (3:1 for large text) |
| 2.1.1 Keyboard | All interactive elements reachable and operable via keyboard |
| 2.4.3 Focus order | Tab order follows visual/logical reading order |
| 2.4.7 Focus visible | Focused elements have a visible focus indicator |
| 3.3.2 Labels or instructions | Every input has a visible label or accessible name |
| 4.1.2 Name, role, value | Custom widgets have correct ARIA roles and states |

**Screen reader testing (manual but essential):**

- **macOS:** VoiceOver (built-in, Cmd+F5)
- **Windows:** NVDA (free) or JAWS
- **Linux:** Orca (GNOME built-in)
- Test critical user flows: navigation, forms, dynamic content updates, error states.

## Prevention

**CI pipeline with axe-core:**

```yaml
# GitLab CI
a11y-audit:
  stage: test
  image: mcr.microsoft.com/playwright:v1.49.0-noble
  script:
    - npm ci
    - npm run build
    - npm run start &
    - npx wait-on http://localhost:3000
    - npx playwright test tests/a11y/
  allow_failure: false
```

**Pre-commit linting:**

```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: a11y-lint
        name: Accessibility lint
        entry: npx eslint --no-warn-ignored
        language: system
        files: \.(tsx|jsx|vue)$
```

**Process rules:**

- Every new UI component must pass axe-core with zero violations before merge.
- Design reviews must include contrast ratio checks (use browser DevTools or Figma plugins).
- Include keyboard-only navigation in manual QA checklists.
- Run Lighthouse accessibility audit nightly; alert on score regression below threshold.
- Maintain an a11y exceptions register for known issues with remediation deadlines.
