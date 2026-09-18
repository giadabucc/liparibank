"""Orchestrator BUGGY — subagent lanciati sequenzialmente."""

import asyncio
from claude_agent_sdk import query, ClaudeAgentOptions

SUBAGENTS = [
    ("code-reviewer-banking-domain", "..."),
    ("security-reviewer", "..."),
    ("performance-reviewer", "..."),
    ("rest-contract-reviewer", "..."),
]


async def run_subagent(name, desc, target, cid):
    # ... chiamata Claude Agent SDK ...
    pass


async def main(target):
    cid = "abc-123"

    # BUG: sequenziale. Aspetta che il subagent N finisca prima di lanciare N+1.
    # Tempo totale ≈ 4 × T_avg invece di T_max.
    results = []
    for name, desc in SUBAGENTS:
        result = await run_subagent(name, desc, target, cid)
        results.append(result)

    return results
