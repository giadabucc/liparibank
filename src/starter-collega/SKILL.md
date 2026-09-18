---
name: compliance-aml-check
description: Verifica compliance AML di un cambiamento di codice del LipariBank
# BUG: allowed-tools include Edit + Write. La skill è di CHECK, non deve modificare file.
allowed-tools: [Read, Grep, Glob, Edit, Write, Bash]
---

# Compliance AML Check

Verifica i 5 controlli AML (soglie, PEP, watchlist, audit trail, SOS).
