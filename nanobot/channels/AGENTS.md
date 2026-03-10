# CHANNELS — Platform Adapters

8 chat platform adapters + seedbot subprocess bridge, managed by ChannelManager with ACL enforcement.

## STRUCTURE

```
channels/
├── base.py              # ENTRY: BaseChannel ABC (start, stop, send, is_allowed)
├── manager.py           # ChannelManager — lazy init, outbound dispatch
├── telegram.py          # Telegram (polling/webhook)
├── slack.py             # Slack (Socket Mode)
├── discord.py           # Discord
├── feishu.py            # Feishu (Lark)
├── whatsapp.py          # WhatsApp
├── qq.py                # QQ
├── matrix.py            # Matrix/Element
├── dingtalk.py          # DingTalk
├── email.py             # Email adapter
├── mochat.py            # MoChat adapter
└── seedbot.py           # Subprocess bridge to seedbot (stdin/stdout, <<<SEEDBOT_DONE>>> marker)
```

## KEY PATTERNS

### BaseChannel Interface
```python
class BaseChannel(ABC):
    async def start(self) -> None: ...    # Long-running listener
    async def stop(self) -> None: ...     # Cleanup
    async def send(self, msg: OutboundMessage) -> None: ...
```
All channels receive `config` + `bus: MessageBus` in constructor.

### Message Flow
Inbound: platform event → `_handle_message(sender_id, chat_id, content, media, metadata)` → `is_allowed()` ACL check → `bus.publish_inbound(InboundMessage)`.
Outbound: `bus.subscribe_outbound()` → `ChannelManager` → route to correct adapter → `adapter.send(OutboundMessage)`.

### ChannelManager
Lazy initializes only enabled channels from config. Dispatches outbound messages to the correct adapter based on `channel_name` field.

### Seedbot Bridge
`seedbot.py` communicates via subprocess stdin/stdout. Writes task → reads until `<<<SEEDBOT_DONE>>>` sentinel. Config: `channels.seedbot.enabled`, `script_path`, `working_dir`, `allow_from`.

## ANTI-PATTERNS

- Never bypass `is_allowed()` ACL check — security boundary for who can interact
- Never send messages outside `BaseChannel.send()` — all outbound goes through the bus
- Never block in `start()` — it must be an async long-running task
- Seedbot marker `<<<SEEDBOT_DONE>>>` is protocol-critical — don't change it
