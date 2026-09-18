> Nota: alcuni file esistono in più varianti sotto `parte-N/` — confrontale, ognuna contiene un'impostazione diversa dello stesso pezzo.

# G1 Bonus — Hook PostToolUse blocca tutti i tool per errore matcher

## Sintomo

Lo studente configura un hook per loggare le chiamate MCP. Dopo il primo prompt Claude Code va in errore continuo: ogni tool call ritorna *"hook returned non-zero exit code"*. Claude Code di fatto smette di funzionare.

## Come riprodurlo

1. Configura `.claude/settings.json` con `BUGGY/settings.json` (matcher `".*"` su PostToolUse + `exit 1` come fallback)
2. Avvia `claude` in qualsiasi cartella
3. Ogni invocazione di tool (Read, Grep, Bash) → exit 1 dell'hook → Claude considera fallita la chiamata
4. **Bug**: Claude Code paralizzato da un hook restrittivo, niente avanzamento


---

# G1 Bug 1 — Subagent con `tools: ["*"]` (allowlist permissiva)

## Sintomo

Il subagent funziona. Lo studente è contento. **Bug invisibile** finché Claude, durante una review che dovrebbe essere read-only, decide di eseguire `rm -rf` perché il prompt utente diceva "puliamo il workspace" o "rimuovi i file inutilizzati".

## Come riprodurlo

1. Crea subagent con `BUGGY/code-reviewer.md` (`tools: ["*"]`)
2. Invoca con prompt ambiguo: `claude "review il codice e elimina i file test inutilizzati"`
3. Claude assume di poter usare qualsiasi tool. Eseguirà `Bash(rm test/...)` e modificherà file con `Edit`.
4. Atteso: il subagent reviewer NON deve eseguire shell distruttivi né modificare file. È un reviewer.


---

# G1 Bug 2 — Subagent description vaga (routing automatico non funziona)

## Sintomo

Il subagent esiste in `.claude/agents/code-reviewer.md`. Quando lo studente scrive *"review il codice di MovementService.java"*, Claude **non lo invoca automaticamente** — fa la review nella conversation principale, ignorando il subagent.

L'unico modo per usarlo è invocarlo esplicitamente con `Task(subagent_type="code-reviewer", ...)` — vanifica il routing automatico.

## Come riprodurlo

1. Crea subagent con `BUGGY/code-reviewer.md` (`description: Reviewer di codice`)
2. Nel REPL Claude Code: `> review MovementService.java`
3. Claude fa la review da solo, senza invocare il subagent
4. **Bug**: routing automatico fallisce per description troppo generica


---

# G1 Bug 3 — Skill `allowed-tools` include Edit (skill di check modifica codice)

## Sintomo

Skill `compliance-aml-check` viene attivata su un prompt AML. Claude, mentre fa il check, "decide" di **fixare** uno dei problemi rilevati editando il file. La skill che doveva essere *check-only* diventa accidentalmente *check-and-fix*.
