# AGENT — Core Execution Loop

Message bus consumer → context builder → LLM chat loop → tool execution → response dispatch. The brain of nanobot.

## STRUCTURE

```
agent/
├── loop.py              # ENTRY: AgentLoop — message processing, LLM iteration, tool execution
├── context.py           # ContextBuilder — history assembly, runtime context injection
├── memory.py            # MemoryStore — session consolidation, long-term archival
├── subagent.py          # SubagentManager — background task delegation
├── skills.py            # Skill loading and execution
└── tools/               # Built-in tools
    ├── registry.py      # ToolRegistry — central tool discovery
    ├── shell.py         # ExecTool — shell command execution
    ├── filesystem.py    # ReadFile, WriteFile, EditFile, ListDir
    ├── web.py           # WebFetchTool, WebSearchTool
    ├── message.py       # MessageTool — outbound messaging
    ├── spawn.py         # SpawnTool — subagent spawning
    └── cron.py          # CronTool — scheduled tasks
```

## KEY PATTERNS

### Agent Loop
```
bus.subscribe() → _process_message() → _run_agent_loop():
  while iteration < max_iterations:
    response = provider.chat(messages, tools)
    if response.has_tool_calls:
      for tool_call in response.tool_calls:
        result = tools.execute(name, args)  # max 500 chars
      continue
    else:
      break  # final text response
```

### Context Building
`ContextBuilder` assembles: system prompt + skills + memory + session history + tool results. Smart truncation respects prompt cache optimization (70% token savings on repeated prefixes).

### Subagent Spawning
`SubagentManager.spawn(task, label)` → `asyncio.create_task()` → runs separate agent loop (no message/spawn tools) → announces result via bus. Session-scoped tracking: `_session_tasks[key]`.

### Memory Consolidation
Background task triggers when unconsolidated messages ≥ `memory_window`. Consolidates into long-term memory store with poisoning prevention.

## ANTI-PATTERNS

- Tool results capped at `_TOOL_RESULT_MAX_CHARS = 500` — don't increase without considering context budget
- Subagents get restricted tools (no message, no spawn) — prevents infinite recursion
- Never bypass `ContextBuilder` — it handles truncation and cache optimization
- <500 LOC discipline applies to this module — don't add features, extract them
