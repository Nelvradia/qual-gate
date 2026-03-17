# OWASP LLM Top 10 Checklist

Mapped to the target project's architecture.

- [ ] LLM01 — Prompt Injection: Input sanitization (L3), permission gates (L1), output validation (L4)
- [ ] LLM02 — Insecure Output Handling: Response validation before tool execution
- [ ] LLM03 — Training Data Poisoning: N/A (using pre-trained models, not fine-tuning)
- [ ] LLM04 — Model Denial of Service: Timeout configuration, rate limiting
- [ ] LLM05 — Supply Chain Vulnerabilities: Model integrity (SHA-256 verification)
- [ ] LLM06 — Sensitive Information Disclosure: Privacy tier enforcement, no Restricted data in prompts
- [ ] LLM07 — Insecure Plugin Design: Permission service validates all tool/skill calls
- [ ] LLM08 — Excessive Agency: Tier system limits autonomous actions
- [ ] LLM09 — Overreliance: Confidence signaling, "I don't know" behavior
- [ ] LLM10 — Model Theft: Local inference only, no model exposure via API
