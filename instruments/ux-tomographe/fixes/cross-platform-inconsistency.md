---
title: "Fix: Cross-Platform Inconsistency"
status: current
last-updated: 2026-03-19
instrument: ux-tomographe
severity-range: "Minor--Major"
---

# Fix: Cross-Platform Inconsistency

## What this means

Your application renders or behaves differently across browsers, devices, or screen sizes in ways
that degrade the user experience. This includes layout breakage at certain viewport widths,
missing functionality in specific browsers, inconsistent component appearance between platforms,
or responsive breakpoints that leave content unreadable or unreachable. Minor findings are
cosmetic differences (slightly different font rendering, minor spacing shifts). Major findings
indicate broken layouts, missing interactive elements, or features that fail entirely on
supported platforms.

## How to fix

### TypeScript / React

**Use a design system with cross-platform tokens:**

```tsx
// Design tokens — single source of truth for spacing, colour, typography
// tokens.ts
export const tokens = {
  spacing: {
    xs: "0.25rem",   // 4px
    sm: "0.5rem",    // 8px
    md: "1rem",      // 16px
    lg: "1.5rem",    // 24px
    xl: "2rem",      // 32px
  },
  breakpoints: {
    sm: "640px",
    md: "768px",
    lg: "1024px",
    xl: "1280px",
  },
  colors: {
    primary: "hsl(220, 65%, 50%)",
    error: "hsl(0, 72%, 51%)",
    // Never use raw hex/rgb — always reference tokens
  },
} as const;
```

**Responsive component with CSS Modules:**

```tsx
// Card.module.css
.card {
  padding: var(--spacing-md);
  display: grid;
  gap: var(--spacing-sm);
}

@media (min-width: 768px) {
  .card {
    grid-template-columns: 1fr 2fr;
  }
}

// Card.tsx
import styles from "./Card.module.css";

export function Card({ title, children }: CardProps) {
  return (
    <article className={styles.card}>
      <h3>{title}</h3>
      <div>{children}</div>
    </article>
  );
}
```

**Avoid platform-specific CSS hacks — use feature queries instead:**

```css
/* BAD: browser-specific hack */
_:-ms-fullscreen, .selector { /* IE11 only */ }

/* GOOD: feature query with fallback */
.grid-layout {
  display: flex;
  flex-wrap: wrap;
}

@supports (display: grid) {
  .grid-layout {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  }
}
```

### TypeScript / Vue

**Use platform-consistent component libraries:**

```vue
<script setup lang="ts">
// Use a design system that normalises cross-browser differences
// Examples: Vuetify, PrimeVue, Headless UI (unstyled, you control rendering)
import { useMediaQuery } from "@vueuse/core";

const isMobile = useMediaQuery("(max-width: 768px)");
</script>

<template>
  <nav :class="isMobile ? 'nav-mobile' : 'nav-desktop'">
    <slot />
  </nav>
</template>

<style scoped>
/* Use logical properties for RTL support */
.nav-desktop {
  padding-inline: 2rem;
  display: flex;
  gap: 1rem;
}

.nav-mobile {
  padding-inline: 1rem;
  display: flex;
  flex-direction: column;
}
</style>
```

### CSS Best Practices (all frameworks)

**Reset and normalise:**

```css
/* Use a modern CSS reset — eliminates cross-browser default inconsistencies */
/* Option A: Include modern-normalize (npm install modern-normalize) */
@import "modern-normalize";

/* Option B: Minimal reset */
*,
*::before,
*::after {
  box-sizing: border-box;
  margin: 0;
  padding: 0;
}

html {
  -moz-text-size-adjust: none;
  -webkit-text-size-adjust: none;
  text-size-adjust: none;
}
```

**Use logical properties for internationalisation:**

```css
/* BAD: physical properties break in RTL layouts */
.card {
  margin-left: 1rem;
  padding-right: 2rem;
  text-align: left;
}

/* GOOD: logical properties adapt to writing direction */
.card {
  margin-inline-start: 1rem;
  padding-inline-end: 2rem;
  text-align: start;
}
```

**Safe font stacks:**

```css
/* System font stack — consistent rendering, no FOUT */
body {
  font-family:
    system-ui,
    -apple-system,
    "Segoe UI",
    Roboto,
    "Noto Sans",
    "Liberation Sans",
    sans-serif,
    "Apple Color Emoji",
    "Segoe UI Emoji";
}

/* Monospace stack */
code {
  font-family:
    ui-monospace,
    "Cascadia Code",
    "Source Code Pro",
    Menlo,
    Consolas,
    "DejaVu Sans Mono",
    monospace;
}
```

### General

**Define a browser/device support matrix:**

Create a support matrix document and reference it in your CI configuration:

```yaml
# .browserslistrc — consumed by Autoprefixer, Babel, PostCSS, etc.
>= 0.5%
last 2 versions
Firefox ESR
not dead
not op_mini all
```

**Responsive design testing checklist:**

| Breakpoint | Viewport | What to verify |
|---|---|---|
| Mobile S | 320px | No horizontal scroll, text readable, touch targets >= 44px |
| Mobile L | 425px | Navigation usable, forms completable |
| Tablet | 768px | Layout transitions correctly, no orphaned columns |
| Laptop | 1024px | Multi-column layouts render, sidebars appear |
| Desktop | 1440px | Content does not stretch excessively, max-width applied |

**Cross-browser testing with Playwright:**

```typescript
import { test, expect, devices } from "@playwright/test";

// playwright.config.ts — test across browsers and devices
export default {
  projects: [
    { name: "chromium", use: { ...devices["Desktop Chrome"] } },
    { name: "firefox", use: { ...devices["Desktop Firefox"] } },
    { name: "webkit", use: { ...devices["Desktop Safari"] } },
    { name: "mobile-chrome", use: { ...devices["Pixel 7"] } },
    { name: "mobile-safari", use: { ...devices["iPhone 14"] } },
  ],
};

// tests/visual/layout.spec.ts
test("card grid renders consistently across viewports", async ({ page }) => {
  await page.goto("/dashboard");
  await expect(page.locator(".card-grid")).toBeVisible();
  // Visual regression: compare screenshots across browsers
  await expect(page).toHaveScreenshot("dashboard-grid.png", {
    maxDiffPixelRatio: 0.01,
  });
});
```

**Visual regression testing with Playwright screenshots:**

```bash
# Generate baseline screenshots
npx playwright test --update-snapshots

# CI: compare against baselines (fails on visual diff)
npx playwright test
```

## Prevention

**CI pipeline with multi-browser testing:**

```yaml
# GitLab CI
cross-browser-test:
  stage: test
  image: mcr.microsoft.com/playwright:v1.49.0-noble
  script:
    - npm ci
    - npm run build
    - npm run start &
    - npx wait-on http://localhost:3000
    - npx playwright test --reporter=html
  artifacts:
    when: always
    paths:
      - playwright-report/
    expire_in: 1 week
  allow_failure: false
```

**Autoprefixer in the build pipeline:**

```bash
npm install --save-dev autoprefixer postcss
```

```js
// postcss.config.js
export default {
  plugins: {
    autoprefixer: {},
  },
};
```

**Process rules:**

- Every UI component must be tested at minimum 3 breakpoints (mobile, tablet, desktop)
  before merge.
- Visual regression screenshots are committed as test baselines. Intentional changes
  require updating snapshots explicitly (`--update-snapshots`).
- Use `browserslist` to define supported targets. Build tools (Babel, PostCSS, SWC)
  automatically transpile and prefix based on this config.
- Review responsive behaviour during code review — screenshots or recordings of the
  component at each breakpoint should be included in the MR description.
- Run cross-browser tests nightly at minimum; on every MR for UI-touching changes.
