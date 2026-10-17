from __future__ import annotations

import unittest
from typing import List
from autochat.engine.reflex import ReflexRule, ReflexTier
from autochat.engine.two_tier import (
    DeepReasoningTier,
    InferenceProvider,
    TwoTierEngine,
)
from autochat.perception.parser import ParsedMessage


class MockInferenceProvider:
    def __init__(self, response: str = "Tập trung đẩy đường trên đi!") -> None:
        self.response = response
        self.last_prompt = ""

    def generate(self, prompt: str) -> str:
        self.last_prompt = prompt
        return self.response


class TwoTierEngineTests(unittest.TestCase):
    def test_reflex_tier_triggers_on_matching_pattern(self) -> None:
        rule = ReflexRule(
            pattern=r"(?i)\b(chào|hello|hi)\b",
            canned_response="Chào bạn, mình đang trong trận nhé!",
        )
        tier1 = ReflexTier(rules=[rule])
        mock_provider = MockInferenceProvider()
        tier2 = DeepReasoningTier(provider=mock_provider)

        engine = TwoTierEngine(reflex_tier=tier1, reasoning_tier=tier2)

        msg = ParsedMessage(speaker="Teammate", text="Hello anh em", is_self=False, raw_line="")
        draft, tier_used = engine.process_message(msg, history=[])

        self.assertEqual(draft, "Chào bạn, mình đang trong trận nhé!")
        self.assertEqual(tier_used, "reflex")
        # LLM was not called
        self.assertEqual(mock_provider.last_prompt, "")

    def test_falls_back_to_reasoning_tier_when_no_reflex_matches(self) -> None:
        rule = ReflexRule(
            pattern=r"(?i)\b(chào|hello|hi)\b",
            canned_response="Chào bạn!",
        )
        tier1 = ReflexTier(rules=[rule])
        mock_provider = MockInferenceProvider(response="Đang combat rồng, đợi 30s")
        tier2 = DeepReasoningTier(provider=mock_provider)

        engine = TwoTierEngine(reflex_tier=tier1, reasoning_tier=tier2)

        msg = ParsedMessage(speaker="Teammate", text="Cần hỗ trợ bot gấp", is_self=False, raw_line="")
        draft, tier_used = engine.process_message(msg, history=[])

        self.assertEqual(draft, "Đang combat rồng, đợi 30s")
        self.assertEqual(tier_used, "reasoning")
        self.assertIn("Cần hỗ trợ bot gấp", mock_provider.last_prompt)

    def test_ignores_self_message(self) -> None:
        tier1 = ReflexTier(rules=[])
        mock_provider = MockInferenceProvider()
        tier2 = DeepReasoningTier(provider=mock_provider)

        engine = TwoTierEngine(reflex_tier=tier1, reasoning_tier=tier2)

        msg = ParsedMessage(speaker="Me", text="Hello", is_self=True, raw_line="")
        draft, tier_used = engine.process_message(msg, history=[])

        self.assertIsNone(draft)
        self.assertEqual(tier_used, "none")


if __name__ == "__main__":
    unittest.main()
