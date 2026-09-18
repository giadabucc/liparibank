---
name: compliance-aml-check
description: Verifica compliance AML (Anti-Money Laundering) di un cambiamento di codice. Da attivare quando il task riguarda movimento di denaro, audit, transazioni, segnalazioni sospette, o quando l'utente cita esplicitamente AML / antiriciclaggio.
---

# Compliance AML Check — LipariBank

Quando questa skill è attiva, applica i seguenti controlli a ogni cambiamento di codice in revisione:

## 1. Soglie operative

Movimenti > 10.000 EUR devono essere flaggati per review umana.
Movimenti > 5.000 EUR devono essere loggati come `audit.threshold-medium`.
Verifica nel codice: `if (amount.compareTo(new BigDecimal("10000")) > 0)` o equivalente.

## 2. PEP (Politically Exposed Persons)

Customer marcato come PEP deve avere flag `customer.isPep == true` salvato in DB.
Movimenti da/per PEP devono triggerare alert via `complianceService.notify(...)`.

## 3. Watchlist screening

Ogni nuovo Customer deve essere passato per il watchlist check al momento del create.
Verifica chiamata a `watchlistService.screen(fiscalCode)` nel `CustomerService.create()`.

## 4. Audit trail completo

Ogni `MovementEntity` deve avere:
- `correlationId` (tracciabilità cross-service)
- `executedBy` (userId che ha originato la transazione)
- `ipAddress` (origine richiesta, dal `JwtAuthenticationFilter`)
- `executedAt` (timestamp con timezone UTC)

Manca uno di questi = finding HIGH.

## 5. Segnalazione operazione sospetta (SOS)

Pattern noti:
- Operazioni multiple < soglia singola ma > soglia aggregata in 24h (smurfing)
- Trasferimenti circolari A→B→A
- Conti dormienti che riprendono attività improvvisamente

Per il bootcamp NON implementiamo la detection completa (richiede ML/streaming).
Verifica solo che il codice abbia ganci (`@Aspect` o `MovementInterceptor`) per future integrazioni.

## Output

Quando applicabile, segnala violazioni in formato:
- **[CRITICAL]** missing audit field — file:line — fix proposto
- **[HIGH]** missing watchlist check — file:line
- **[MEDIUM]** missing threshold flag — file:line
- **[LOW]** missing SOS hook — file:line