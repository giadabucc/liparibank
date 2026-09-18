---
name: compliance-aml-check
description: Use this skill whenever code, PR o endpoint riguardano movimento di denaro, audit, transazioni, segnalazioni sospette, screening PEP/watchlist, o quando l'utente cita esplicitamente AML / antiriciclaggio. Verifica la compliance AML (Anti-Money Laundering) di un cambiamento di codice per LipariBank.
allowed-tools: Read, Grep, Glob
---

# Compliance AML Check — LipariBank

Quando questa skill è attiva, applica i seguenti controlli a ogni cambiamento di codice in revisione.

## 1. Soglie operative

Movimenti > 10.000 EUR devono essere flaggati per review umana.
Movimenti > 5.000 EUR devono essere loggati come `audit.threshold-medium`.
Verifica nel codice: `if (amount.compareTo(new BigDecimal("10000")) > 0)` o equivalente.
Nel `MovementService.transfer()` attuale questo controllo non esiste — è un gap atteso nel bootcamp, ma va segnalato esplicitamente.

## 2. PEP (Politically Exposed Persons)

`Customer` dovrebbe avere un flag `isPep` persistito in DB. Oggi `Customer.java` non ha questo campo (solo `firstName`, `lastName`, `fiscalCode`, `createdAt`).
Movimenti da/per un customer PEP dovrebbero triggerare un alert verso un componente di compliance dedicato (oggi inesistente nel progetto).
Segnala l'assenza come gap HIGH, non come bug — è un requisito da implementare, non una regressione.

## 3. Watchlist screening

Ogni nuovo `Customer` dovrebbe essere passato per un watchlist check al momento della creazione.
Nel progetto attuale **non esiste un flusso di creazione customer esposto**: ci sono solo `Customer` (entity) e `CustomerRepository`, nessun `CustomerService`/`CustomerController`. Segnala entrambi i gap: assenza del flusso di creazione e, a maggior ragione, assenza dello screening.

## 4. Audit trail completo

Ogni `Movement` (classe reale: `com.lipari.bank.movement.Movement`) dovrebbe avere:
- `correlationId` — nel progetto esiste già un `CorrelationIdFilter` che genera un correlationId per request, ma il valore non viene mai scritto su `Movement`. Verifica se è così anche nel codice in review.
- `executedBy` — userId che ha originato la transazione. Oggi assente su `Movement`.
- `ipAddress` — origine della richiesta. Oggi assente; il filtro di autenticazione reale si chiama `JwtFilter` (non `JwtAuthenticationFilter`) e non estrae né propaga l'IP.
- `executedAt` — questo campo esiste già ed è valorizzato correttamente in `MovementService.transfer()`.

Manca uno dei primi tre campi = finding HIGH.

## 5. Segnalazione operazione sospetta (SOS)

Pattern noti da verificare (basta un punto d'aggancio predisposto, non serve detection ML/streaming):
- Operazioni multiple sotto soglia singola ma sopra soglia aggregata in 24h (smurfing)
- Trasferimenti circolari A→B→A
- Conti dormienti che riprendono attività improvvisamente

Per il bootcamp non implementiamo la detection completa. Verifica solo che il codice abbia un punto di estensione (es. un `@Aspect` su `MovementService.transfer()`, o un listener/interceptor dedicato) per future integrazioni. Oggi non esiste: segnalalo come gap architetturale, severity LOW/MEDIUM a seconda del contesto.

## Output

Quando applicabile, segnala violazioni in questo formato:
- **[CRITICAL]** ... — file:line — fix proposto
- **[HIGH]** missing audit field / missing PEP flag / missing watchlist hook — file:line
- **[MEDIUM]** missing threshold flag — file:line
- **[LOW]** missing SOS extension point — file:line
- Sezione "Fuori scope per questo stub" per i gap strutturali noti e già accettati nel bootcamp

Non ripetere findings di code quality/sicurezza generica (JWT hardcoded, N+1, uso di `double` per importi) — quelli sono di competenza del subagent `code-reviewer-banking-domain`.
