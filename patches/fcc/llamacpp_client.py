"""Llama.cpp provider implementation."""
"""Custom: enforces max_tokens >= 8192 for Ornith reasoning blocks."""

from typing import Any

from providers.base import ProviderConfig
from providers.defaults import LLAMACPP_DEFAULT_BASE
from providers.transports.anthropic_messages import AnthropicMessagesTransport


_MIN_MAX_TOKENS = 8192


def _ensure_min_max_tokens(
    body: dict[str, Any],
    _request_data: Any,
    _thinking_enabled: bool,
) -> None:
    """Ornith burns tokens on <think> blocks; ensure we don't run out before
    producing visible output."""
    body["max_tokens"] = max(body.get("max_tokens", _MIN_MAX_TOKENS), _MIN_MAX_TOKENS)


class LlamaCppProvider(AnthropicMessagesTransport):
    """Llama.cpp provider using native Anthropic Messages endpoint."""

    def __init__(self, config: ProviderConfig):
        super().__init__(
            config,
            provider_name="LLAMACPP",
            default_base_url=LLAMACPP_DEFAULT_BASE,
        )

    def _build_request_body_with_resolved_thinking(
        self, request: Any, *, thinking_enabled: bool
    ) -> dict:
        from providers.transports.anthropic_messages.request_policy import (
            build_native_messages_request_body,
        )

        return build_native_messages_request_body(
            request,
            thinking_enabled=thinking_enabled,
            policy=self._request_policy,
            postprocessors=(_ensure_min_max_tokens,),
        )
