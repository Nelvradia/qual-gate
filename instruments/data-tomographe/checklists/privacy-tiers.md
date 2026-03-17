# Privacy Tier Checklist
- [ ] Public: system config, no encryption
- [ ] Internal: operational data, standard SQLite
- [ ] Confidential: personal data, SQLCipher
- [ ] Restricted: health/financial, SQLCipher + audit
- [ ] No Confidential/Restricted data stored in Public/Internal databases
- [ ] Access to Restricted data is audit-logged
