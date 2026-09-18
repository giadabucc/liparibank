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
│   │   │   │   ├── CustomerRepository.java
│   │   │   │   ├── CustomerService.java
│   │   │   │   └── CustomerController.java
│   │   │   ├── account/
│   │   │   │   ├── Account.java                 ← entity con `balance: BigDecimal`
│   │   │   │   ├── AccountRepository.java
│   │   │   │   ├── AccountService.java
│   │   │   │   └── AccountController.java
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

```java
@Service
public class AccountService {
    public List<AccountDto> listAllWithMovements() {
        // ⚠️ ANTI-PATTERN: N+1 query
        return accountRepo.findAll().stream()
            .map(a -> {
                List<Movement> movements = movementRepo.findByAccountId(a.getId());  // N+1!
                return new AccountDto(a, movements);
            })
            .toList();
    }
}
```

Il subagent `performance-reviewer` deve trovarlo. Severity: MEDIUM. Pattern enterprise: `@EntityGraph` o JPQL `JOIN FETCH` per single-query con join.

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
