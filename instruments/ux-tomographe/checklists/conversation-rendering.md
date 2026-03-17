# Conversation Rendering Checklist

Verify chat messages render correctly on both platforms.

## Message Types
- [ ] Plain text messages render correctly
- [ ] Markdown bold/italic/links render
- [ ] Code blocks render with syntax highlighting
- [ ] Multi-line code blocks have copy button
- [ ] Lists (ordered + unordered) render correctly
- [ ] Tables render readably (or fallback gracefully)
- [ ] Long messages scroll without overflow
- [ ] Very short messages don't look broken

## Special Content
- [ ] Approval cards render inline with action buttons
- [ ] Briefing summaries render with expandable sections
- [ ] Habit check-in cards render with tap-to-log
- [ ] Error messages styled distinctly (not just red text)
- [ ] System messages (connected, disconnected) styled distinctly

## Interaction
- [ ] Typing indicator during LLM generation
- [ ] Streaming text appears incrementally (not all-at-once)
- [ ] Send button disabled when input empty
- [ ] Shift+Enter for newline (Desktop), Enter to send
- [ ] Message timestamps visible (relative: "2 min ago")
- [ ] Scroll-to-bottom on new message
- [ ] Can scroll up through history without auto-scroll-down
