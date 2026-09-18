> Nota: alcuni file esistono in più varianti sotto `parte-N/` — confrontale, ognuna contiene un'impostazione diversa dello stesso pezzo.

# G2 Bonus — Nessun cost tracking né budget hard limit

## Sintomo

Lo studente lancia `code_review_suite.py` e va a prendere un caffè. Torna 30 minuti dopo: l'orchestrator è ancora running. Un subagent è andato in loop su una codebase grande, ha consumato 500K token (vs i 50K previsti). Costo stimato: 4-5 USD per una singola run. Mese a 100 run = 400-500 USD bruciati.

# In main, dopo gather:
total_tokens = sum(r.tokens for r in results)
cost_usd = total_tokens * COST_PER_TOKEN
elapsed_s = time.time() - start
try:
    check_budget(elapsed_s, total_tokens, cost_usd)
except BudgetExceeded as e:
    print(f"⚠️ BUDGET WARNING: {e}")
```

In produzione si può rendere bloccante (raise + abort). In sandbox sufficiente warn-only.


---

# G2 Bug 1 — 4 subagent lanciati sequenzialmente invece di paralleli

## Sintomo

`code_review_suite.py` funziona, produce il report. Ma è **lentissimo**: 4-8 minuti per una review che dovrebbe richiederne 1-2. Token totali identici al pattern parallelo, ma tempo totale = somma dei 4 subagent invece di max.

# BUGGY
results = []
for name, desc in SUBAGENTS:
    result = await run_subagent(name, desc, target, cid)
    results.append(result)

# FIXED
tasks = [run_subagent(name, desc, target, cid) for name, desc in SUBAGENTS]
results = await asyncio.gather(*tasks)
```

Differenza concettuale: `asyncio.gather` schedula tutti i coroutine come task contemporanei al loop event. Il loop esegue il prossimo task quando uno è in `await` (es. waiting su HTTP).


---

# G2 Bug 2 — `max_turns` mancante → default 10, agent runaway

## Sintomo

Orchestrator chiama `query()` senza specificare `max_turns`. Tutto funziona finché il subagent risolve il task in <10 turni. Quando un task complesso richiede 15-20 turni, il subagent si interrompe a metà → findings parziali, output incompleto.

In altri casi peggiori (loop tool/risposta), agent runaway che consuma 100K+ token prima di accorgersene.


---

# G2 Bug 3 — Subagent reviewer con tools include `Edit`

## Sintomo

Il subagent `security-reviewer` viene invocato per una review. Durante l'analisi, "decide" che il problema rilevato (es. hardcoded JWT secret) va **fixato subito** — chiama `Edit` sul file e modifica il codice. Il PR diventa diverso da quello dell'autore. Lo studente non se ne accorge fino al diff next-day.
