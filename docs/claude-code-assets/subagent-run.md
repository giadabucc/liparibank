# Run trace — subagent `code-reviewer-banking-domain`

- **Data**: 2026-09-18
- **PR reale**: https://github.com/giadabucc/liparibank/pull/1 (branch `feature/validate-transfer-amount` → `master`)
- **Modalità di invocazione**: esplicita, dal terminale Claude Code, con lo stesso prompt suggerito dal README dello starter:

  > "Use the code-reviewer-banking-domain subagent to review this PR: focus on AccountService and MovementService."

- **Contesto passato al subagent**: percorso locale del repo, branch/base da confrontare (`git diff master...feature/validate-transfer-amount`), link alla PR, descrizione della modifica (validazione `amount` in `MovementService.transfer()` come difesa in profondità sul `@DecimalMin` già presente su `TransferRequest`).

## Diff sotto review

```java
+        if (req.getAmount() == null || req.getAmount().compareTo(BigDecimal.ZERO) <= 0) {
+            throw new IllegalArgumentException("amount must be greater than zero");
+        }
```
`src/main/java/com/lipari/bank/movement/MovementService.java:36-38`

## Output del subagent (integrale)

### CRITICAL

**C1 — Broken Object-Level Authorization (IDOR) su tutti gli endpoint conto/movimento**
`MovementController.java:19-22,27-30`, `AccountController.java:18-23,29-36`

`JwtFilter` autentica l'utente e mette solo lo username nel `SecurityContext`, senza ruoli né claim di ownership. Nessun controller verifica che l'utente autenticato sia il proprietario del conto:
- `GET /api/accounts/{id}` — qualunque utente autenticato legge saldo di qualsiasi conto.
- `GET /api/movements?accountId=X` — stesso problema.
- `POST /api/movements/transfer` — `req.getFromAccountId()` non viene mai verificato contro l'utente autenticato: un utente può disporre un bonifico da un conto che non è il suo.

Fix proposto: risolvere `customerId` dal principal autenticato e verificare `account.getCustomerId() == callerCustomerId` in `AccountController` e in `MovementService.transfer()` per `fromAccountId`.

**C2 — Race condition / lost update sul saldo (double-spend classico)**
`MovementService.java:44-56`

`findById` legge senza lock, `Account` non ha campo `@Version`. Due transazioni concorrenti sullo stesso conto leggono lo stesso saldo, superano entrambe il check "insufficient funds" e producono un lost update.

Fix proposto: locking pessimistico (`@Lock(PESSIMISTIC_WRITE)`) con ordine di acquisizione deterministico tra i due conti, oppure `@Version` (optimistic locking) con gestione esplicita di `OptimisticLockException`.

**C3 — JWT secret hardcoded nel sorgente**
`JwtService.java:23` — confermato, anti-pattern intenzionale A del bootcamp.

### HIGH

- **H1** — Nessun idempotency key su `transfer()` (anti-pattern intenzionale B, limite accettato per il bootcamp, ma segnalato).
- **H2** — N+1 query in `AccountController.listAllWithMovements()` (anti-pattern intenzionale C). Fix: query batch `findByAccountIdIn` + `groupingBy`.
- **H3** — Audit trail assente: nessun log in `MovementService.transfer()`, nessuna colonna actor/userId su `Movement`, correlationId disponibile in MDC ma mai loggato lì.
- **H4** — Nessun controllo su `Account.status` prima di movimentare denaro (un conto `CLOSED` può comunque operare).

### MEDIUM

- **M1** — Self-transfer check (`fromAccountId.equals(toAccountId)`) non null-safe — incoerente con la difesa appena introdotta dalla PR.
- **M2** — Nessun controllo di valuta tra `from` e `to`.
- **M3** — `GlobalExceptionHandler.handleGeneric()` non logga le eccezioni: 500 senza traccia server-side.
- **M4** — Credenziali datasource in chiaro in `application.yml`.
- **M5** — Nessun test per il nuovo ramo di validazione introdotto dalla PR.

### LOW

- **L1** — `@Autowired` su field in `TransferIT.java:18` (severità bassa: è codice di test).

### OK — nessun finding

- Uso di `BigDecimal` corretto e consistente ovunque, confronti sempre via `compareTo`.
- Password storage: `BCryptPasswordEncoder`, strength 10, nessun MD5/SHA-1/plaintext.
- `@Transactional` su metodo pubblico, nessun side-effect fuori transazione.
- `Optional.get()` mai usato senza guardia.
- Nessun `throw new RuntimeException(e)` che perde lo stack.

### Riepilogo priorità (dal subagent)

> Prima di qualunque discussione su idempotency o N+1 (già note e accettate come limiti bootcamp), le due cose che bloccherei in un contesto reale sono C1 (IDOR — chiunque autenticato può disporre bonifici da conti altrui) e C2 (race condition sul saldo): sono esattamente i due bug bancari "classici" che questa PR aveva l'occasione di intercettare, dato che tocca proprio `transfer()`, ma che restano fuori scope della modifica proposta.

## Osservazioni

Il subagent ha correttamente rispettato il proprio scope dichiarato in `description` (attivarsi su PR che toccano `domain/movement`/`domain/account`) e ha allargato la review oltre il diff puntuale quando il contesto lo giustificava, come istruito. Ha trovato tutti e 3 gli anti-pattern intenzionali dello starter **più** due CRITICAL reali (IDOR, race condition) non pianificati — a conferma che il valore del subagent non si limita a "trovare le esche note" ma generalizza al dominio banking descritto nel suo system prompt.
