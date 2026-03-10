# PROVIDERS — LLM Provider Interface

Abstract provider protocol with registry-based discovery. Supports OpenAI, Azure, LiteLLM, Codex, and custom providers.

## STRUCTURE

```
providers/
├── base.py                      # ENTRY: LLMProvider ABC, LLMResponse, ToolCallRequest
├── registry.py                  # ProviderSpec — metadata for 20+ providers
├── openai_codex_provider.py     # OAuth-based Codex provider
├── azure_openai_provider.py     # Azure OpenAI
├── litellm_provider.py          # LiteLLM gateway (100+ models)
├── custom_provider.py           # Custom/self-hosted provider
└── transcription.py             # Audio transcription provider
```

## KEY PATTERNS

### Provider Interface
```python
class LLMProvider(ABC):
    async def chat(
        self, messages, tools, model, max_tokens, temperature, reasoning_effort
    ) -> LLMResponse
```

### LLMResponse
```python
@dataclass
class LLMResponse:
    content: str | None
    tool_calls: list[ToolCallRequest]
    finish_reason: str = "stop"
    usage: dict[str, int]
    reasoning_content: str | None      # Kimi, DeepSeek-R1
    thinking_blocks: list[dict] | None # Anthropic extended thinking
```

### Provider Registry
`ProviderSpec` in `registry.py` maps: name → env_key, litellm_prefix, is_gateway, is_local, model_overrides. Supports keyword matching for provider auto-detection.

### Message Sanitization
`LLMProvider._sanitize_empty_content()` replaces empty text content that causes provider 400 errors. Applied before every `chat()` call.

## ANTI-PATTERNS

- Never skip message sanitization — empty content causes provider rejections
- Never hardcode provider API keys — use env vars mapped in `ProviderSpec.env_key`
- Never add providers without `ProviderSpec` entry — auto-detection depends on it
