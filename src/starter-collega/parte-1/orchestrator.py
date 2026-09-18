"""BUGGY — niente budget tracking."""

import asyncio
import time
from claude_agent_sdk import query, ClaudeAgentOptions


async def main(target):
    start = time.time()
    tasks = [run_subagent(name, target) for name in SUBAGENTS]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # BUG: nessun controllo su token totali, elapsed, cost.
    # Un agent runaway può consumare 500K token (~5 USD) senza che nessuno se ne accorga.

    # Stampa solo report finale, senza warning su consumi anomali
    print(synthesize_report(results))
