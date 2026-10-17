from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Optional
from ..perception.parser import ParsedMessage


@dataclass(frozen=True)
class ReflexRule:
    pattern: str
    canned_response: str

    def matches(self, text: str) -> bool:
        return bool(re.search(self.pattern, text))


class ReflexTier:
    """Fast reflex engine (< 5ms) for immediate keyword/pattern responses."""

    def __init__(self, rules: Optional[List[ReflexRule]] = None) -> None:
        self.rules: List[ReflexRule] = rules or []

    def add_rule(self, rule: ReflexRule) -> None:
        self.rules.append(rule)

    def evaluate(self, message: ParsedMessage) -> Optional[str]:
        if message.is_self:
            return None
        for rule in self.rules:
            if rule.matches(message.text):
                return rule.canned_response
        return None
