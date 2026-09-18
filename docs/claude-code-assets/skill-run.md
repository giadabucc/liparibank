# Run trace — skill `compliance-aml-check` (attivazione automatica)

- **Data**: 2026-09-18
- **PR di riferimento**: https://github.com/giadabucc/liparibank/pull/1
- **Modalità di invocazione**: **automatica**, non esplicita. Il prompt inviato a Claude Code non nomina la skill:

  > "Prima di mergiare la PR #1, verifica anche se il transfer rispetta la normativa antiriciclaggio e se ci sono rischi di operazioni sospette non intercettate."

- **Trigger riconosciuti**: le parole "antiriciclaggio" e "operazioni sospette" hanno fatto match con la `description` di `.claude/skills/compliance-aml-check/SKILL.md`, che le include esplicitamente come parole chiave di routing.

## Output prodotto

**[HIGH]** Nessun flag PEP su `Customer` — `Customer.java` (nessun campo).
Manca `isPep` e qualunque hook di notifica per movimenti da/verso clienti politicamente esposti.

**[HIGH]** Watchlist screening assente, e manca il flusso di creazione cliente stesso — non esiste `CustomerService`/`CustomerController`, solo entity + repository.

**[HIGH]** Audit trail incompleto su `Movement` — presente solo `executedAt`. Mancano `correlationId` (il `CorrelationIdFilter` esiste ma non scrive mai su `Movement`), `executedBy`, `ipAddress`.

**[MEDIUM]** Nessuna soglia di segnalazione sugli importi in `MovementService.transfer()` — la PR valida solo `amount <= 0`, nessun controllo lato alto (soglie 10k/5k EUR).

**[LOW]** Nessun punto di estensione (`@Aspect`/interceptor) per future detection SOS (structuring, transfer circolari, conti dormienti).

### Fuori scope per questo stub
- Detection ML/streaming per SOS
- Integrazione reale con liste sanzioni OFAC/UE

### Nota sulla PR specifica
La modifica in review (validazione `amount <= 0`) è ortogonale alla compliance AML: non introduce né risolve i gap sopra. Nessun blocco al merge da parte della skill; i gap HIGH restano backlog separato.

## Osservazioni

Conferma pratica della differenza subagent/skill (punto 6 della checklist): questa skill ha girato **inline**, nella stessa conversazione che aveva appena ricevuto il trace del subagent (poteva riferirsi alla PR #1 senza che gliela ridescrivessi da zero), mentre il subagent `code-reviewer-banking-domain` (vedi `subagent-run.md`) è partito con **contesto isolato** e ha avuto bisogno di istruzioni esplicite su repo/branch/PR per orientarsi.
