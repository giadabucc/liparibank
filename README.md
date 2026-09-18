# LipariBank Spring Target — progetto Java di partenza

> Progetto Spring Boot 3.3 / Java 21 **minimale ma realistico** che funge da **target di review** per gli agent del bootcamp. È il codice su cui i 4 subagent, la skill `compliance-aml-check`, il `code-review-suite.py` orchestrator e il `finbank-mcp` server lavoreranno.
>
> **Quando usarlo**: se vieni dal Bootcamp Microservizi 2gg del catalogo Lipari, salta questo e usa il tuo LipariBank Multi-Service (più ricco). Se vieni dal Bootcamp Claude Code **standalone** e non hai un progetto Spring banking in mano, clona questo come fallback.

---

## Cosa è (e cosa NON è)

**È:**
- Un backend REST Spring Boot 3.3 single-service con i tre concetti banking minimi: `Customer`, `Account`, `Movement`
- ~10 classi Java + 2 changeset Liquibase + Dockerfile multi-stage
- Endpoint `POST /api/transfer` che fa debit/credit tra due conti in transazione locale
- JWT auth base (token statefulless con HS256)
- Tre **anti-pattern intenzionali** inseriti come "esca" per i subagent reviewer: vedi sezione [Anti-pattern presenti per il review](#anti-pattern-presenti-per-il-review)

**Non è:**
- Un sistema production-grade (manca circuit breaker, retry, audit trail completo, validazione completa, multi-currency, …)
- Un sistema multi-service (non parla con altri servizi via REST/gRPC/WebSocket — c'è solo un Spring service)
- Un'app deployabile su K8s/cloud (no profili dev/staging/prod, no observability, no health probe production)

Il bootcamp Claude Code non insegna Spring. Questo stub esiste solo come **target del review**, non come architettura modello.

---

## Struttura

```
liparibank-spring-target/
├── pom.xml
├── Dockerfile
├── README.md                                    ← questo file
├── src/
│   ├── main/
│   │   ├── java/com/lipari/bank/
│   │   │   ├── LipariBankApplication.java       ← main + @SpringBootApplication
│   │   │   ├── common/
│   │   │   │   ├── CorrelationIdFilter.java     ← MDC filter
│   │   │   │   └── GlobalExceptionHandler.java  ← @RestControllerAdvice
│   │   │   ├── customer/
│   │   │   │   ├── Customer.java                ← entity
│   │   │   │   └── CustomerRepository.java      ← ⚠️ nessun Service/Controller (vedi Difetti)
│   │   │   ├── account/
│   │   │   │   ├── Account.java                 ← entity con `balance: BigDecimal`
│   │   │   │   ├── AccountRepository.java
│   │   │   │   └── AccountController.java       ← ⚠️ anti-pattern C qui dentro, non in un AccountService (vedi Difetti)
│   │   │   ├── movement/
│   │   │   │   ├── Movement.java                ← entity (deposit, withdraw, transfer)
│   │   │   │   ├── MovementRepository.java
│   │   │   │   ├── MovementService.java         ← @Transactional sul transfer
│   │   │   │   ├── MovementController.java      ← POST /api/transfer
│   │   │   │   └── dto/
│   │   │   │       ├── TransferRequest.java
│   │   │   │       └── TransferResponse.java
│   │   │   ├── security/
│   │   │   │   ├── SecurityConfig.java
│   │   │   │   ├── JwtFilter.java
│   │   │   │   └── JwtService.java              ← ⚠️ anti-pattern A (vedi sotto)
│   │   │   └── web/
│   │   │       └── AuthController.java          ← POST /api/auth/login
│   │   └── resources/
│   │       ├── application.yml
│   │       └── db/changelog/
│   │           ├── 001-base-schema.yaml
│   │           └── db.changelog-master.yaml
│   └── test/
│       └── java/com/lipari/bank/
│           └── TransferIT.java                  ← happy path test
```

Totale: ~25 file, ~600 righe Java + ~80 righe YAML.

---

## Setup rapido

```bash
# 1. Clone (o copia questa cartella nel tuo workspace)
git clone <questo-repo>
cd liparibank-spring-target

# 2. Run con docker-compose (MySQL incluso)
docker compose up -d
./mvnw spring-boot:run

# 3. Test rapido
curl -X POST http://localhost:8080/api/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"username":"alice","password":"alice123"}'
# → {"token":"eyJhbGc..."}

JWT=$(...)
curl -X POST http://localhost:8080/api/transfer \
  -H "Authorization: Bearer $JWT" \
  -H 'Content-Type: application/json' \
  -d '{"fromAccountId":1,"toAccountId":2,"amount":100.00}'
# → 200 OK con i due saldi aggiornati
```

---

## Come usarlo dentro il bootcamp Claude Code

### Setup del PW del candidato

Il candidato clona/copia questa cartella nel proprio workspace. Poi:

```bash
# 1. Apri Claude Code dalla cartella
cd liparibank-spring-target/
claude

# 2. Claude vede il repo. Il candidato durante il bootcamp:
#    - G1: scrive 1 subagent + 1 skill nella cartella .claude/
#    - G2: scrive lo script orchestrator `code-review-suite.py` che girerà su questo repo
#    - G3: scrive `finbank-mcp/server.py` che espone metodi su questo backend
```

### Cosa il candidato fa al G1

- Crea `.claude/agents/code-reviewer-banking-domain.md` (vedi `solutions/code-review-suite/.claude/agents/` per il riferimento)
- Lo invoca a mano dal terminal Claude Code: *"Use the code-reviewer-banking-domain subagent to review this PR: focus on AccountService and MovementService"*
- Il subagent **trova i 3 anti-pattern intenzionali** elencati sotto + altre osservazioni emergenti

### Cosa il candidato fa al G2

- Scrive `code-review-suite.py` Claude Agent SDK orchestrator
- Lo script invoca i 4 subagent (banking domain, performance, REST contract, security) in **parallelo** via `Task` tool
- Output: `review-report.md` unificato con findings categorizzati per severity

### Cosa il candidato fa al G3

- Scrive `finbank-mcp/server.py` che espone:
  - Tool `get_account_balance(account_id)` → chiama HTTP `GET /api/accounts/{id}` di questo backend
  - Tool `list_recent_movements(account_id, since, limit)` → chiama HTTP `GET /api/movements?accountId={id}` di questo backend
  - Tool `simulate_transfer_what_if(...)` → simula un transfer senza commit (richiede endpoint dedicato lato Spring, da aggiungere a mano se serve)
- Lo connette a Claude Desktop o Claude Code e fa query in linguaggio naturale: *"Mostrami i movimenti del conto 1 della settimana scorsa"*

---

## Anti-pattern presenti per il review

Sono **3 anti-pattern intenzionali** inseriti nel codice come "esca" per i subagent reviewer del bootcamp. Il candidato non dovrebbe leggere questa sezione **prima** di lanciare il primo subagent — il punto del bootcamp è che il subagent li trovi.

(Se sei il docente o stai consegnando il PW, ecco il dettaglio per la review.)

**Anti-pattern A — `JwtService.java`: JWT secret hardcoded**

```java
@Service
public class JwtService {
    // ⚠️ ANTI-PATTERN: secret hardcoded nel codice
    private static final String SECRET = "demo-jwt-secret-for-bootcamp-banking-system";
    ...
}
```

Il subagent `security-reviewer` deve trovarlo. Severity: HIGH. Pattern enterprise: leggere da `application.yml` con valore iniettato da env var (`${JWT_SECRET}`), che a sua volta è iniettato da K8s Secret / Vault.

**Anti-pattern B — `MovementService.transfer()`: nessun controllo idempotency**

```java
@Transactional
public TransferResponse transfer(TransferRequest req) {
    // ⚠️ ANTI-PATTERN: nessun Idempotency-Key, retry sicuro impossibile
    Account from = accountRepo.findById(req.getFromAccountId()).orElseThrow();
    Account to = accountRepo.findById(req.getToAccountId()).orElseThrow();
    from.setBalance(from.getBalance().subtract(req.getAmount()));
    to.setBalance(to.getBalance().add(req.getAmount()));
    ...
}
```

Il subagent `code-reviewer-banking-domain` deve trovarlo. Severity: HIGH. Pattern enterprise: header `Idempotency-Key` UUID dal client, tabella `processed_idempotency_keys` con TTL 24h, check come prima istruzione.

**Anti-pattern C — `AccountRepository.findAll()` chiamato in loop**

Nota: nella prima stesura di questo README l'anti-pattern era descritto dentro una classe `AccountService` — quella classe non è mai esistita nel progetto. Il codice reale è direttamente in `AccountController` (vedi [Difetti dello starter trovati e corretti](#difetti-dello-starter-trovati-e-corretti)):

```java
@GetMapping("/with-movements")
public List<AccountWithMovements> listAllWithMovements() {
    // ANTI-PATTERN C (intenzionale): N+1 query.
    return accountRepo.findAll().stream()
        .map(a -> new AccountWithMovements(a, movementRepo.findByAccountIdOrderByExecutedAtDesc(a.getId())))
        .toList();
}
```

Il subagent `performance-reviewer` (o, in questo progetto, `code-reviewer-banking-domain`) deve trovarlo. Severity: MEDIUM. Pattern enterprise: query batch (`findByAccountIdIn` + `groupingBy`) dato che non c'è una relazione JPA diretta tra `Account` e `Movement` che permetta `@EntityGraph`/`JOIN FETCH`.

---

## Dipendenze (`pom.xml`)

- `spring-boot-starter-web` 3.3.4
- `spring-boot-starter-data-jpa`
- `spring-boot-starter-security`
- `jjwt-api` + `jjwt-impl` + `jjwt-jackson` 0.12.6
- `mysql-connector-j`
- `org.liquibase:liquibase-core`
- Java 21

Dipendenze di test: `spring-boot-starter-test`, `testcontainers:mysql`.

---

## Note operative

- **Non è il LipariBank Multi-Service del Bootcamp Microservizi 2gg**. Quello ha 4 servizi (account, movement, customer, notification) che parlano fra loro via REST + gRPC + WebSocket. Questo è single-service, più semplice. Per il bootcamp Claude Code basta.
- **Non è production-grade**. Pattern intenzionalmente "junior" per dare ai subagent qualcosa da trovare. Se vai a colloquio mostrando *questo* codice come *tuo*, ti chiedono perché ci sono i 3 anti-pattern. Riusalo come *codice target di review*, non come portfolio.
- **Lingua del codice**: identificatori inglesi (Account, Movement, transfer, balance) — standard di mercato Italia 2026. Commenti in inglese per coerenza con docs Spring.

---

## Claude Code Assets

Asset creati per il project work Claude Code (G1), con evidenza di esecuzione reale.

### Subagent — `.claude/agents/code-reviewer-banking-domain.md`

- **Cosa fa**: code review domain-aware per banking (transazioni `@Transactional`, idempotency, `BigDecimal`, password BCrypt, JWT secret handling, audit trail, N+1).
- **Come si attiva**: automaticamente su PR che toccano `domain/movement`, `domain/account`, `domain/user` (la `description` include "Use proactively before merging..."), oppure esplicitamente: *"Use the code-reviewer-banking-domain subagent to review this PR: focus on AccountService and MovementService"*.
- **Esecuzione**: contesto **isolato** — non ha accesso alla cronologia della conversazione, va istruito da zero su repo/branch/PR.
- **Run trace reale**: [docs/claude-code-assets/subagent-run.md](docs/claude-code-assets/subagent-run.md), eseguito su [PR #1](https://github.com/giadabucc/liparibank/pull/1).

### Skill — `.claude/skills/compliance-aml-check/SKILL.md`

- **Cosa fa**: verifica compliance AML/antiriciclaggio — soglie di segnalazione, flag PEP, watchlist screening, audit trail, hook per segnalazione operazioni sospette (SOS).
- **Come si attiva**: automaticamente quando la richiesta menziona AML/antiriciclaggio/compliance/operazioni sospette (routing via `description`), oppure esplicitamente digitando `/compliance-aml-check`.
- **Esecuzione**: **inline** — condivide il contesto della conversazione in corso.
- **Run trace reale (attivazione automatica, skill mai nominata esplicitamente)**: [docs/claude-code-assets/skill-run.md](docs/claude-code-assets/skill-run.md).

### Config — `.claude/settings.json`

- **Cosa fa**: `model: sonnet` (alias portabile), `permissions.allow` su `Read`/`Grep`/`Glob` (niente prompt di conferma per operazioni read-only), hook `PostToolUse` di audit log su tutti i tool (matcher `.*`) che scrive una riga JSON (`ts`, `tool`, `input`) su `.claude/audit.log` per ogni tool call.
- **Perché il comando dell'hook è `try {...} catch {}; exit 0`**: `src/starter-collega/settings.json` ha un hook `PostToolUse` che fa `exit 1` dopo il log — un hook con exit code non-zero fa fallire la tool call agli occhi di Claude Code, e con matcher `.*` questo blocca **ogni** tool, paralizzando la CLI al primo prompt. Il mio hook non fallisce mai (testato anche con input vuoto/malformato: exit code sempre `0`), quindi logga senza mai bloccare nulla.
- **Prova che scatta davvero**: verificato live in sessione — dopo aver scritto il file, ogni tool call successiva (inclusa una `Read` di prova) è comparsa in `.claude/audit.log` senza bisogno di riavviare Claude Code.

### Subagent vs skill vs slash command

- **Subagent**: contesto isolato, tool/model propri. Attivabile sia automaticamente (Claude legge la `description` e delega da solo) sia esplicitamente — l'invocazione non è ciò che lo distingue dalla skill.
- **Skill**: contesto inline, condiviso con la conversazione corrente. Anche qui attivabile sia automaticamente (via `description`) sia esplicitamente (`/nome-skill`).
- **Slash command personalizzato**: nella versione attuale di Claude Code *è* una skill invocata esplicitamente — non esiste più un formato `.claude/commands/*.md` separato. Restano a parte solo i comandi built-in della CLI (`/help`, `/clear`, `/resume`, `/config`...), che sono logica hardcoded, non definibile dall'utente.
- **L'asse di distinzione reale è quindi**: isolato (subagent) vs inline (skill), non automatico vs esplicito.

## Difetti dello starter trovati e corretti

### Difetti nello starter-collega (`src/starter-collega/`)

Ho scelto di **implementare da zero** (opzione esplicitamente prevista dal PW) invece di partire dal codice di Gino, ma prima ho letto i suoi 4 bug documentati per non riprodurli. Eccoli, con dove si trova la correzione nel mio codice:

1. **Hook `PostToolUse` con `exit 1` blocca tutta la CLI.** `src/starter-collega/settings.json` — hook con matcher `.*` che fa `echo ... && exit 1` dopo ogni tool call. Un hook che ritorna exit code non-zero fa considerare fallita la tool call: con matcher `.*` **ogni** Read/Grep/Bash fallisce, Claude Code si paralizza al primo prompt.
   **Fix applicato nel mio `.claude/settings.json`**: il comando dell'hook di audit è avvolto in `try {...} catch {}; exit 0` — logga se può, non fallisce mai, non blocca nessuna tool call anche se il parsing dell'input va male. Testato con input valido e input vuoto/rotto: `exit code` sempre `0` in entrambi i casi.

2. **Subagent con `tools: ["*"]`.** `src/starter-collega/parte-3/code-reviewer.md` — allowlist permissiva: un reviewer che può usare *qualsiasi* tool, incluso `Bash(rm -rf ...)`, se il prompt utente è ambiguo ("elimina i file inutilizzati").
   **Fix applicato**: il mio `.claude/agents/code-reviewer-banking-domain.md` usa `tools: Read, Grep, Glob, Bash` — niente `Edit`/`Write`, coerente col fatto che è un reviewer, non un fixer.

3. **Subagent con `description` troppo generica.** `src/starter-collega/parte-2/code-reviewer.md` — `description: Reviewer di codice`: nessuna keyword di dominio, il routing automatico non scatta mai, il subagent è invocabile solo esplicitamente.
   **Fix applicato**: la mia `description` parte con "Use proactively before merging any PR that touches domain/movement, domain/account o domain/user" ed è ricca di keyword di dominio (transazioni, idempotency, BigDecimal, JWT) — vedi [docs/claude-code-assets/subagent-run.md](docs/claude-code-assets/subagent-run.md) per la prova che il routing funziona.

4. **Skill con `allowed-tools` che include `Edit`/`Write`.** `src/starter-collega/SKILL.md` — una skill di solo-check (`compliance-aml-check`) con `allowed-tools: [Read, Grep, Glob, Edit, Write, Bash]`: Claude può decidere di "fixare" un problema invece di segnalarlo, sforando lo scope dichiarato (check-only).
   **Fix applicato**: la mia skill usa `allowed-tools: Read, Grep, Glob` — nessuna possibilità di modificare file, solo di leggerli e produrre findings.

### Difetti extra trovati (cartella `.opencode/`, non richiesti dal PW ma reali)

Nel repo esisteva anche una cartella `.opencode/` (config per OpenCode CLI, "Path B" del bootcamp) con un proprio tentativo di subagent/skill — diversa da `starter-collega/` e non richiesta esplicitamente dal testo del PW, ma con difetti reali che ho comunque documentato. Lasciata nel repo — esclusi `node_modules/` e `opencode.local.json` — come testimonianza "as-found".

1. **Subagent e skill nella cartella sbagliata.** `code-reviewer-banking-domain.md` e `compliance-aml-check/SKILL.md` esistevano già, ma sotto `.opencode/agents/` e `.opencode/skills/` — cartelle lette da OpenCode CLI, non da Claude Code, che quindi non li avrebbe mai caricati.
   **Fix**: ricreati sotto `.claude/agents/` e `.claude/skills/`.

2. **Model ID inesistente nel subagent.** Il frontmatter originale specificava `model: claude-sonnet-4-6`, un ID che non corrisponde a nessun modello Claude attuale — l'agent sarebbe fallito all'invocazione.
   **Fix**: sostituito con l'alias `sonnet`, più stabile nel tempo di un ID puntuale.

3. **Skill AML scritta contro un codice che non esiste.** La skill originale citava `MovementEntity`, `JwtAuthenticationFilter`, `complianceService.notify(...)`, `watchlistService.screen(...)` e un metodo `CustomerService.create()`: nessuna di queste classi/metodi esiste nel progetto reale (le classi vere sono `Movement` e `JwtFilter`; `CustomerService`, `ComplianceService`, `WatchlistService` non esistono affatto).
   **Fix**: riscritta la skill sui nomi di classe reali, trasformando i riferimenti a codice inesistente in gap espliciti da segnalare (es. "manca il flusso di creazione customer", non "verifica `CustomerService.create()`").

4. **`.gitignore` incompleto.** Ignorava solo `opencode.local.json`, non `target/` (build Maven, migliaia di `.class`) né `.opencode/node_modules/` (migliaia di file). Un `git add -A` senza fix avrebbe pushato tutto questo su un repository pubblico.
   **Fix**: aggiunte le entry mancanti.

5. **README non allineato al codice reale.** La struttura documentata elencava `CustomerService.java`, `CustomerController.java` e `AccountService.java`, nessuno dei quali esiste nel progetto — in particolare l'anti-pattern C era descritto come se vivesse in `AccountService.listAllWithMovements()`, mentre il metodo reale è direttamente in `AccountController` (non esiste alcuna classe `AccountService`).
   **Fix**: struttura e blocco di codice dell'anti-pattern C corretti in questo stesso README (vedi sezioni [Struttura](#struttura) e [Anti-pattern presenti per il review](#anti-pattern-presenti-per-il-review)).

6. **Frontmatter YAML malformato in `hello-banking.md`.** Il file (`.opencode/agents/hello-banking.md`) chiude il blocco frontmatter con `-----------------` invece di `---`, un delimitatore non standard.
   **Non corretto** (file fuori scope Claude Code, mantenuto com'è come testimonianza "as-found"), ma documentato qui.

7. **API key in chiaro in `opencode.local.json`.** Il file (correttamente in `.gitignore`) contiene una API key OpenCode Zen in chiaro su disco. Non è un difetto dello starter Claude Code in senso stretto, ma una nota di sicurezza operativa: se il `.gitignore` non fosse stato corretto (punto 4) o il file venisse copiato/zippato altrove, la chiave sarebbe esposta.

**Bonus — difetti nel codice applicativo trovati dal subagent** (non nello starter Claude Code, ma nel progetto Spring stesso): il subagent `code-reviewer-banking-domain`, invocato sulla PR reale, ha trovato due bug CRITICAL non pianificati oltre ai 3 anti-pattern intenzionali — **IDOR** su `transfer`/`getAccount`/`listByAccount` (nessun controllo che l'utente autenticato sia proprietario del conto) e una **race condition sul saldo** (nessun lock/`@Version`, possibile lost update / double-spend). Dettagli in [docs/claude-code-assets/subagent-run.md](docs/claude-code-assets/subagent-run.md).
