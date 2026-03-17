# Glossary Compliance Checklist (K2)
- [ ] No bare "domain" (use permission_domain, life_domain, adapter_domain)
- [ ] No bare "context" (use conversation_context, life_context, code_context)
- [ ] No bare "template" without category qualifier in DB queries
- [ ] No bare "trigger" (use proactive_trigger, workflow_trigger)
- [ ] No bare "session" (use conversation_session, time_session)
- [ ] lint_glossary.py CI job passes
