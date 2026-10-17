from __future__ import annotations

from typing import List, Optional, Protocol, Tuple, runtime_checkable
from ..perception.parser import ParsedMessage
from .reflex import ReflexTier


@runtime_checkable
class InferenceProvider(Protocol):
    def generate(self, prompt: str) -> str: ...


class DeepReasoningTier:
    """Deliberate reasoning tier using LLM inference (e.g. Gemini Flash / Ollama / Syrin Pool)."""

    DEFAULT_SYSTEM_PROMPT = (
        "Bạn là trợ lý game/chat thông minh, ngắn gọn, tự nhiên, phản hồi lịch sự bằng tiếng Việt."
    )

    def __init__(
        self,
        provider: InferenceProvider,
        system_prompt: Optional[str] = None,
    ) -> None:
        self.provider = provider
        self.system_prompt = system_prompt or self.DEFAULT_SYSTEM_PROMPT

    def generate(self, message: ParsedMessage, history: List[ParsedMessage]) -> str:
        # Build prompt from recent history + new incoming message
        lines = [self.system_prompt, "\nLịch sử trò chuyện gần nhất:"]
        for past_msg in history[-5:]:
            role = "Tôi" if past_msg.is_self else past_msg.speaker
            lines.append(f"{role}: {past_msg.text}")
        lines.append(f"{message.speaker}: {message.text}")
        lines.append("Hãy đưa ra câu trả lời ngắn gọn (1 câu):")

        prompt = "\n".join(lines)
        raw_response = self.provider.generate(prompt)
        return raw_response.strip()


class TwoTierEngine:
    """Orchestrates Tier 1 (Reflex) and Tier 2 (Deep Reasoning)."""

    def __init__(
        self,
        reflex_tier: ReflexTier,
        reasoning_tier: DeepReasoningTier,
    ) -> None:
        self.reflex_tier = reflex_tier
        self.reasoning_tier = reasoning_tier

    def process_message(
        self,
        message: ParsedMessage,
        history: Optional[List[ParsedMessage]] = None,
    ) -> Tuple[Optional[str], str]:
        if message.is_self:
            return None, "none"

        hist = history or []

        # 1. Tier 1 Reflex check (< 5ms)
        reflex_reply = self.reflex_tier.evaluate(message)
        if reflex_reply:
            return reflex_reply, "reflex"

        # 2. Tier 2 Deep Reasoning check
        reasoning_reply = self.reasoning_tier.generate(message, hist)
        if reasoning_reply:
            return reasoning_reply, "reasoning"

        return None, "none"
