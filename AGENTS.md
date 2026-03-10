# NANOBOT - KNOWLEDGE BASE

**Generated:** 2026-03-10
**Commit:** 65ab476
**Branch:** main

## OVERVIEW

Ultra-lightweight personal AI assistant — 99% fewer LOC than OpenClaw with full agent capabilities. Multi-channel (Telegram, Slack, Discord, Feishu, QQ, WhatsApp, Matrix, DingTalk), MCP tool integration, multi-provider LLM (OpenAI, Azure, LiteLLM), session management, cron tasks. Production-ready with PyPI distribution.

Stack: Python 3.11+, MCP, asyncio, SSE streaming

## STRUCTURE

```
.
├── nanobot/                 # Main package
│   ├── agent/               # Core agent loop + subagent support
│   │   ├── loop.py          # Main agent execution loop
│   │   └── subagent.py      # Subagent delegation
│   ├── providers/           # LLM providers (OpenAI, Azure, LiteLLM, Codex)
│   ├── session/             # Session + history management
│   ├── config/              # Schema, loader, paths
│   ├── bus/                 # Event queue + message bus
│   ├── cron/                # Scheduled task service
│   ├── cli/                 # CLI commands
│   └── templates/           # Workspace templates (memory, etc.)
├── channels/                # Multi-channel adapters (Telegram, Slack, etc.)
├── tests/                   # Unit + integration tests
└── core_agent_lines.sh      # Line count verification script
```

## WHERE TO LOOK

| Task | Location | Notes |
|------|----------|-------|
| Agent execution | `nanobot/agent/loop.py` | Main agent loop with MCP tool calls |
| Subagent delegation | `nanobot/agent/subagent.py` | Spawn child agents for subtasks |
| Add LLM provider | `nanobot/providers/` | base.py protocol, registry.py registration |
| Session management | `nanobot/session/manager.py` | History, context, poisoning protection |
| MCP integration | `nanobot/agent/loop.py` | SSE streaming, tool execution |
| Cron tasks | `nanobot/cron/service.py` | Scheduled reminders + reload guards |
| CLI commands | `nanobot/cli/commands.py` | Start, config, workspace management |
| Channel adapters | `channels/` | Telegram, Slack, Discord, Feishu, etc. |
| Config schema | `nanobot/config/schema.py` | YAML validation |
| Event bus | `nanobot/bus/events.py` | Inter-component messaging |
| SeedbotChannel | `channels/seedbot.py` | Subprocess bridge to seedbot (Bash Codex agent) |

## CHANNELS

### SeedbotChannel
Subprocess stdin/stdout bridge to seedbot (Bash Codex agent).
- File: `channels/seedbot.py`
- Config: `channels.seedbot.enabled`, `script_path`, `working_dir`, `allow_from`
- Protocol: writes to stdin, reads stdout until `<<<SEEDBOT_DONE>>>` marker
- Delivery: via MessageBus (same ACL as other channels)
- Test: `tests/test_seedbot_channel.py` (7 tests)

## CONVENTIONS

### Line Count Discipline
- Core agent: <500 LOC (verify: `bash core_agent_lines.sh`)
- **99% reduction** vs OpenClaw (24,000 → <500 LOC)
- Strict minimalism: no feature bloat

### Session Context
- Anti-poisoning: sanitize user input before history save
- Context window: smart truncation + prompt cache optimization
- Thread isolation: per-channel session separation

### Provider Interface
```python
class BaseProvider(Protocol):
    async def complete(
        self, messages: List[Dict], tools: Optional[List] = None
    ) -> AsyncIterator[str]:
        ...
```

### Config Format (YAML)
```yaml
provider: openai
model: gpt-4
channels:
  - type: telegram
    token: ...
mcp_servers:
  - name: filesystem
    command: npx
    args: ["-y", "@modelcontextprotocol/server-filesystem"]
```

## ANTI-PATTERNS (THIS PROJECT)

| Forbidden | Why | Reference |
|-----------|-----|-----------|
| Feature creep beyond core agent | Violates 99% reduction discipline | `README.md` line count promise |
| Unsafe file reads without guards | Windows path traversal risk | v0.1.4.post2 changelog |
| Skipping session dedup | WhatsApp/Telegram duplicate messages | Session manager |
| Hardcoded credentials | Security violation | `SECURITY.md` |
| Blocking I/O in agent loop | Async-first design | `agent/loop.py` |
| Manual provider registration | Use registry pattern | `providers/registry.py` |

## PROVEN RESULTS

**Production Deployment**:
- PyPI package: `nanobot-ai` (13K+ downloads)
- Multi-channel: 8 platforms supported
- MCP SSE: Full streaming support (v0.1.4.post3)
- Session poisoning fix: Hardened context integrity
- Prompt cache: 70% token reduction on repeated contexts

**ClawWork Integration**:
- **Only import target** in ecosystem (`from nanobot import Agent`)
- Proven economic benchmark: $19K agent earnings via nanobot runtime

## COMMANDS

```bash
# Install
pip install nanobot-ai

# Start agent
nanobot start

# Verify line count discipline
bash core_agent_lines.sh

# Run tests
pytest tests/

# Create workspace from template
nanobot workspace create --template memory
```

## HARNESS STATUS

Entry: `.harness/run-gates.sh` (no `justfile` yet)

| Gate | Tool | Status |
|------|------|--------|
| A | black (line-length=100) | ✅ (41 files reformatted) |
| B | ruff lint | ✅ |
| C | lizard complexity (max=23) | ✅ (post-refactor) |
| D | mypy | ✅ |
| E | pytest | ✅ |
| F | integration tests | disabled |

Work chunks committed: `docs/chunks/001` through `docs/chunks/004`

## NOTES

- **Thinking mode**: Experimental `<thinking>` tag support for reasoning transparency
- **Virtual heartbeat**: Tool-call keepalive prevents provider timeouts on long tasks
- **Prompt cache**: Optimized for Claude/GPT prefix caching (70% token savings)
- **Media handling**: Multimodal support (images, audio) across all channels
- **Web proxy**: Configurable SOCKS5/HTTP proxy for network restrictions
- **Windows compatibility**: Path guards for cross-platform safety
- **Release cadence**: Daily fixes + weekly feature releases (see NEWS)
