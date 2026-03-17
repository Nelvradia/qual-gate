# WCAG 2.1 AA Accessibility Checklist

Adapted for the project's target platforms.

## 1. Perceivable
### 1.1 Text Alternatives
- [ ] All non-text content has text alternative (contentDescription / alt / aria-label)
- [ ] Decorative images marked as such (importanceForAccessibility=no / alt="")

### 1.2 Time-Based Media
- [ ] N/A for current scope (no video/audio content in UI)

### 1.3 Adaptable
- [ ] Information structure conveyed through semantics (headings, lists, landmarks)
- [ ] Reading order is meaningful (DOM/Compose order matches visual order)
- [ ] Instructions don't rely solely on shape, size, visual location, or orientation

### 1.4 Distinguishable
- [ ] Color not used as sole means of conveying information
- [ ] Text contrast ratio ≥ 4.5:1 (AA) for normal text
- [ ] Text contrast ratio ≥ 3:1 for large text (≥18pt)
- [ ] Text resizable up to 200% without loss of content
- [ ] No images of text (use actual text)

## 2. Operable
### 2.1 Keyboard Accessible (Desktop)
- [ ] All functionality available via keyboard
- [ ] No keyboard traps (can always Tab/Escape out)
- [ ] Focus indicator visible on all interactive elements

### 2.2 Enough Time
- [ ] No time limits on user actions (or user can extend)
- [ ] Auto-updating content can be paused (typing indicators excluded)

### 2.3 Seizures and Physical Reactions
- [ ] No content flashes more than 3 times per second

### 2.4 Navigable
- [ ] Skip navigation mechanism (Desktop)
- [ ] Page/screen titles are descriptive
- [ ] Focus order is logical
- [ ] Link/button purpose clear from text

### 2.5 Input Modalities
- [ ] Touch targets ≥ 48dp (Android) / 44px (Desktop)
- [ ] Pointer gestures have single-pointer alternative
- [ ] Motion-triggered actions have alternative activation

## 3. Understandable
### 3.1 Readable
- [ ] Language of content determinable (lang attribute)
- [ ] Unusual words or abbreviations explained

### 3.2 Predictable
- [ ] Navigation consistent across screens
- [ ] Components that look the same behave the same

### 3.3 Input Assistance
- [ ] Input errors identified and described
- [ ] Labels or instructions provided for user input
- [ ] Error suggestions provided when known

## 4. Robust
### 4.1 Compatible
- [ ] Valid HTML/Compose structure (no broken nesting)
- [ ] Name, role, value exposed for all UI components
- [ ] Status messages programmatically determinable
