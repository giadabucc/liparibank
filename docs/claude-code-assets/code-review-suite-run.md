# Run trace — `code-review-suite.py` (Path B / OpenCode)

- **Data**: 2026-09-18
- **Comando**: `python code-review-suite.py "$(git show c594a45 -- src/main/java/com/lipari/bank/movement/MovementService.java)"`
- **Target**: commit `c594a45` (la validazione amount del G1, PR #1)
- **Path**: B (OpenCode) — nessun credito Claude Pro/Max/API key disponibile per `claude-agent-sdk`.

## Log console (parallelismo — timestamp)

```
Code Review Suite — Run ddac3bc3-dc75-4774-9fc7-7519dff48ee7 (Path B / OpenCode)
Subagents: 4
[ddac3bc3...] 15:58:01 START  code-reviewer-banking-domain
[ddac3bc3...] 15:58:04 START  security-reviewer
[ddac3bc3...] 15:58:07 START  performance-reviewer
[ddac3bc3...] 15:58:10 START  rest-contract-reviewer
[ddac3bc3...] 15:59:11 DONE  code-reviewer-banking-domain: 2 findings, 11391 tokens
[ddac3bc3...] 15:59:53 DONE  performance-reviewer: 0 findings, 20103 tokens
[ddac3bc3...] 16:01:05 DONE  security-reviewer: 4 findings, 25168 tokens
[ddac3bc3...] 16:02:10 ERROR rest-contract-reviewer: 0 findings, 0 tokens

✅ Report saved to review-report-ddac3bc3-dc75-4774-9fc7-7519dff48ee7.md
   Total: 56,662 tokens · $0.000 · 249.1s
```

I 4 START sono a 3s di distanza (stagger deliberato, vedi sotto) ma le esecuzioni si sovrappongono ampiamente (15:58:01→15:59:11 vs 15:58:10→16:02:10): parallelismo reale, non sequenziale — il tempo totale (249s) è vicino alla durata del subagent più lento, non alla somma dei 4 (che avrebbe superato i 15 minuti).

## Report generato (integrale)

**Elapsed**: 249.1s · **Tokens**: 56,662 · **Cost**: $0.000

### code-reviewer-banking-domain
- **[MEDIUM]** `MovementService.java:35` — rifiuto di transfer per amount non valido non loggato/auditato — in banking i tentativi rifiutati vanno tracciati (audit AML). Fix: log WARN con i campi rilevanti prima del throw.
- **[LOW]** `MovementService.java:34` — manca null-check su `req` stesso (solo su `req.getAmount()`), un caller non-controller con `req == null` produce NPE invece di errore controllato.

### security-reviewer
- **[HIGH]** `MovementService.java:44` — Broken object-level authorization (OWASP A01:2021): nessun controllo che il chiamante autenticato sia proprietario di `fromAccountId`. Stesso IDOR già trovato dal subagent del G1.
- **[HIGH]** `MovementService.java:31` — nessun controllo idempotency: retry di rete produce doppio addebito (ANTI-PATTERN B già documentato nel Javadoc).
- **[MEDIUM]** `MovementService.java:36` — la nuova guardia non valida la scala decimale: un importo come 0.001 supera sia `@DecimalMin("0.01")` (compareTo ignora la scala) sia il nuovo check, mentre la colonna `Account.balance` è `precision=19, scale=2`.
- **[LOW]** `MovementService.java:40` — difesa in profondità incompleta: `req`/`fromAccountId`/`toAccountId` nulli causano NPE (500) invece di 400 pulito.

### performance-reviewer
✅ OK no findings

### rest-contract-reviewer
❌ Errore: subprocess timeout after 240s

### Summary
CRITICAL: 0 · HIGH: 2 · MEDIUM: 2 · LOW: 2

## Note tecniche — bug reali trovati e corretti durante lo sviluppo dell'orchestrator

Non difetti di `starter-collega/`, ma bug reali emersi costruendo la pipeline Path B, documentati qui perché rilevanti per "dove il tuo orchestrator può fallire" (sezione Decidi e motiva):

1. **Shim `.cmd` di Windows corrompe gli argomenti.** `asyncio.create_subprocess_exec("opencode", ...)` risolve allo shim npm `opencode.CMD`, che ri-lancia il comando via `cmd.exe`. Un messaggio lungo/multi-riga (system prompt + diff) veniva ri-parsato male da `cmd.exe`, perdendo silenziosamente `--agent`/`--format`: l'agente ricadeva su quello di default (`build`) rispondendo in prosa invece che in JSON — nessun errore, solo dati sbagliati. **Fix**: risolvere l'eseguibile reale (`node_modules/opencode-ai/bin/opencode.exe`) e invocare quello direttamente.
2. **`tokens.total` è cumulativo di sessione, non incrementale.** Sommare `tokens.total` di ogni evento `step_finish` sovrastima drasticamente il conteggio. **Fix**: tenere solo l'ultimo valore osservato.
3. **`database is locked` sotto concorrenza reale.** 4 processi `opencode` simultanei contendono lo stesso storage locale di sessione (SQLite). **Fix**: retry su errori transitori (max 2, backoff crescente) + stagger di 3s tra i lanci (riduce la contesa iniziale restando genuinamente parallelo, vedi log timestamp sopra).
