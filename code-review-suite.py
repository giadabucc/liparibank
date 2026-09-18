"""
code-review-suite.py — orchestrator multi-agent per code review del LipariBank.

Path B (OpenCode): lancia 4 reviewer specializzati in parallelo come subprocess
`opencode run`, invece di claude_agent_sdk. Ogni reviewer riusa il "guscio" di
esecuzione .opencode/agents/reviewer.md (sola lettura, mode: primary, steps: 15)
e riceve come prompt il contenuto di .claude/agents/{name}.md — stesso schema
di dominio del Giorno 1, nessuna duplicazione delle regole di review.
"""

import asyncio
import json
import re
import shutil
import sys
import time
import uuid
from pathlib import Path

if sys.platform == "win32":
    # Console Windows in cp1252 di default: manda in crash i print con emoji/em-dash.
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

AGENTS_DIR = Path(".claude/agents")
OPENCODE_EXEC_AGENT = "reviewer"


def resolve_opencode_binary() -> str:
    """Trova l'eseguibile opencode reale, non lo shim .cmd di npm su Windows.

    asyncio.create_subprocess_exec passa gli argv esattamente cosi' come sono
    solo per un eseguibile nativo. Su Windows uno shim .cmd/.bat viene rilanciato
    internamente via cmd.exe, che ri-parsa la riga di comando con le sue regole
    di quoting: un messaggio lungo/multi-riga con caratteri speciali (es. un
    diff git) viene troncato e i flag dopo di esso (--agent, --format) vengono
    persi. L'eseguibile .exe reale, installato da npm accanto allo shim, evita
    del tutto questo livello di re-parsing.
    """
    shim = shutil.which("opencode")
    if not shim:
        return "opencode"
    if sys.platform == "win32" and shim.lower().endswith((".cmd", ".bat")):
        real_exe = Path(shim).parent / "node_modules" / "opencode-ai" / "bin" / "opencode.exe"
        if real_exe.exists():
            return str(real_exe)
    return shim


OPENCODE_BIN = resolve_opencode_binary()

SUBAGENTS = [
    "code-reviewer-banking-domain",
    "security-reviewer",
    "performance-reviewer",
    "rest-contract-reviewer",
]

TOKEN_BUDGET = 200_000
TIME_BUDGET_SECONDS = 600
COST_BUDGET_USD = 5.0
SUBPROCESS_TIMEOUT_SECONDS = 240
MAX_RETRIES = 2
RETRYABLE_ERROR_MARKERS = ("database is locked", "SQLITE_BUSY")
# 4 processi opencode simultanei contendono lo stesso storage locale di sessione
# (SQLite) e vanno in "database is locked" sotto carico. Uno stagger di pochi
# secondi tra i lanci riduce la contesa iniziale restando comunque genuinamente
# parallelo: ogni run dura decine di secondi, quindi le esecuzioni si sovrappongono
# ampiamente anche con lo stagger (verificabile dai timestamp di log).
STAGGER_SECONDS = 3


class BudgetExceeded(Exception):
    pass


def check_budget(elapsed_s: float, total_tokens: int, cost_usd: float) -> None:
    problems = []
    if elapsed_s > TIME_BUDGET_SECONDS:
        problems.append(f"time {elapsed_s:.0f}s > {TIME_BUDGET_SECONDS}s")
    if total_tokens > TOKEN_BUDGET:
        problems.append(f"tokens {total_tokens} > {TOKEN_BUDGET}")
    if cost_usd > COST_BUDGET_USD:
        problems.append(f"cost ${cost_usd:.2f} > ${COST_BUDGET_USD}")
    if problems:
        raise BudgetExceeded(", ".join(problems))


def load_agent_prompt(name: str) -> tuple[str, str]:
    """Legge .claude/agents/{name}.md, ritorna (description, system_prompt_body)."""
    text = (AGENTS_DIR / f"{name}.md").read_text(encoding="utf-8")
    match = re.match(r"^---\n(.*?)\n---\n(.*)$", text, re.DOTALL)
    if not match:
        return "", text
    frontmatter, body = match.group(1), match.group(2)
    desc_match = re.search(r"^description:\s*(.+)$", frontmatter, re.MULTILINE)
    description = desc_match.group(1).strip() if desc_match else ""
    return description, body.strip()


def extract_json_array(content: str) -> list:
    """Trova il primo array JSON ben formato nel testo (tollerante a prosa attorno)."""
    start = content.find("[")
    end = content.rfind("]") + 1
    if start == -1 or end == 0:
        return []
    try:
        return json.loads(content[start:end])
    except json.JSONDecodeError:
        return []


async def call_opencode_once(message: str) -> tuple[str, int, float, str | None]:
    """Una singola invocazione `opencode run`. Ritorna (text, tokens, cost, error)."""
    proc = await asyncio.create_subprocess_exec(
        OPENCODE_BIN, "run", message,
        "--agent", OPENCODE_EXEC_AGENT,
        "--format", "json",
        "--auto",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    text_parts: list[str] = []
    last_step_tokens = 0
    last_step_cost = 0.0

    try:
        stdout, stderr = await asyncio.wait_for(
            proc.communicate(), timeout=SUBPROCESS_TIMEOUT_SECONDS
        )
        if proc.returncode != 0:
            return "", 0, 0.0, stderr.decode(errors="replace").strip()[:500]

        for line in stdout.decode(errors="replace").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            part = event.get("part", {})
            if event.get("type") == "text" and "text" in part:
                text_parts.append(part["text"])
            elif event.get("type") == "step_finish":
                # "tokens.total" e' il cumulativo di sessione ad ogni step, non un
                # delta: va preso l'ultimo valore visto, mai sommato fra gli step.
                last_step_tokens = part.get("tokens", {}).get("total", last_step_tokens)
                last_step_cost = part.get("cost", last_step_cost) or last_step_cost

        return "\n".join(text_parts), last_step_tokens, last_step_cost, None
    except asyncio.TimeoutError:
        proc.kill()
        await proc.wait()
        return "", 0, 0.0, f"subprocess timeout after {SUBPROCESS_TIMEOUT_SECONDS}s"


async def run_subagent(name: str, target: str, cid: str, stagger_index: int = 0) -> dict:
    if stagger_index:
        await asyncio.sleep(stagger_index * STAGGER_SECONDS)
    print(f"[{cid}] {time.strftime('%H:%M:%S')} START  {name}")
    description, system_prompt = load_agent_prompt(name)

    message = (
        f"{system_prompt}\n\n"
        f"---\n\nReview the following change. Output ONLY the JSON array of findings "
        f"described above, no prose before or after.\n\n{target}"
    )

    text, total_tokens, cost_usd, error = "", 0, 0.0, None
    for attempt in range(MAX_RETRIES + 1):
        text, total_tokens, cost_usd, error = await call_opencode_once(message)
        retryable = error and any(marker in error for marker in RETRYABLE_ERROR_MARKERS)
        if not retryable:
            break
        wait_s = 2 * (attempt + 1)
        print(f"[{cid}] {time.strftime('%H:%M:%S')} RETRY  {name} (attempt {attempt + 1}): {error} — retry in {wait_s}s")
        await asyncio.sleep(wait_s)

    findings = extract_json_array(text) if not error else []

    status = "ERROR" if error else "DONE "
    print(
        f"[{cid}] {time.strftime('%H:%M:%S')} {status} {name}: "
        f"{len(findings)} findings, {total_tokens} tokens"
    )
    return {
        "name": name,
        "description": description,
        "findings": findings,
        "tokens": total_tokens,
        "cost": cost_usd,
        "error": error,
    }


def synthesize_report(results: list, cid: str, total_tokens: int, elapsed_s: float, cost_usd: float) -> str:
    md = f"# Code Review Suite — Run `{cid}`\n\n"
    md += f"**Elapsed**: {elapsed_s:.1f}s · **Tokens**: {total_tokens:,} · **Cost**: ${cost_usd:.3f}\n\n"
    md += "---\n\n"

    severity_count = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}

    for result in results:
        md += f"## {result['name']}\n"
        md += f"_{result['description']}_\n\n"
        if result["error"]:
            md += f"❌ Errore: {result['error']}\n\n"
            continue
        if not result["findings"]:
            md += "✅ OK no findings\n\n"
            continue
        for finding in result["findings"]:
            sev = finding.get("severity", "MEDIUM")
            severity_count[sev] = severity_count.get(sev, 0) + 1
            md += f"- **[{sev}]** `{finding.get('file', '?')}:{finding.get('line', '?')}` — {finding.get('description', '')}\n"
            md += f"  - **Fix**: {finding.get('fix', '')}\n"
        md += "\n"

    md += "---\n\n## Summary\n\n"
    for sev, count in severity_count.items():
        md += f"- {sev}: {count}\n"

    return md


async def main(target: str) -> None:
    cid = str(uuid.uuid4())
    start = time.time()
    print(f"Code Review Suite — Run {cid} (Path B / OpenCode)")
    print(f"Subagents: {len(SUBAGENTS)}")

    tasks = [run_subagent(name, target, cid, stagger_index=i) for i, name in enumerate(SUBAGENTS)]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    clean_results = []
    for name, result in zip(SUBAGENTS, results):
        if isinstance(result, Exception):
            clean_results.append({
                "name": name, "description": "", "findings": [],
                "tokens": 0, "cost": 0.0, "error": str(result),
            })
        else:
            clean_results.append(result)

    elapsed = time.time() - start
    total_tokens = sum(r["tokens"] for r in clean_results)
    cost = sum(r["cost"] for r in clean_results)

    try:
        check_budget(elapsed, total_tokens, cost)
    except BudgetExceeded as e:
        print(f"⚠️  BUDGET WARNING: {e}")

    report = synthesize_report(clean_results, cid, total_tokens, elapsed, cost)
    output_path = Path(f"review-report-{cid}.md")
    output_path.write_text(report, encoding="utf-8")

    print(f"\n✅ Report saved to {output_path}")
    print(f"   Total: {total_tokens:,} tokens · ${cost:.3f} · {elapsed:.1f}s")


if __name__ == "__main__":
    target_arg = sys.argv[1] if len(sys.argv) > 1 else "git diff HEAD~1"
    asyncio.run(main(target_arg))
