# Cross-Platform Parity Checklist

Verify Android and Desktop present consistent experience.

## Core Features (must exist on both)
- [ ] Chat interface with message send/receive
- [ ] Approval flow (Approve / Reject / Discuss buttons)
- [ ] Briefing display with expandable sections
- [ ] Connection status indicator (connected / offline / reconnecting)
- [ ] Pairing flow (token entry → fingerprint → connected)
- [ ] Reconnection with offline message queue

## Data Parity (same data, may differ in layout)
- [ ] Same conversation history visible on both
- [ ] Same briefing content on both
- [ ] Same approval proposals on both
- [ ] Same habit tracking data on both

## Platform-Specific (OK to differ)
- [ ] Android: biometric gate for T3+ (hardware feature)
- [ ] Android: UnifiedPush notifications (mobile-appropriate)
- [ ] Desktop: ⌘K command palette (keyboard-centric)
- [ ] Desktop: system tray integration
- [ ] Desktop: global hotkey (Ctrl+Space)

## Must Not Differ
- [ ] Error messages are consistent (same wording)
- [ ] Confidence indicators are consistent (same visual language)
- [ ] AI personality is consistent (same role, same tone)
