"""BUGGY — max_turns mancante."""

from claude_agent_sdk import query, ClaudeAgentOptions


async def run_subagent(name, target):
    # BUG: max_turns NON specificato. Default = 10.
    # Per orchestrator complessi o codebase grandi, 10 turni si esauriscono → findings parziali.
    async for msg in query(
        prompt=f"Review {target}",
        options=ClaudeAgentOptions(
            cwd=".",
            allowed_tools=["Read", "Grep", "Glob"],
            agent=name,
            # max_turns assente → default 10
        )
    ):
        # ... process ...
        pass
