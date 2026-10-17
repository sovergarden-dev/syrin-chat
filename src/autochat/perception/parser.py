from __future__ import annotations

import re
from collections import deque
from dataclasses import dataclass
from typing import Deque, List, Optional
from .ocr import OcrResult


@dataclass(frozen=True)
class ParsedMessage:
    speaker: str
    text: str
    is_self: bool
    raw_line: str


class TranscriptParser:
    """Parses raw OCR output into structured messages with speaker attribution and deduplication."""

    DEFAULT_PATTERN = re.compile(
        r"^(?:\[(?P<time>[^\]]+)\]\s*)?(?P<speaker>[^:\n\[\]]{2,25})[:：]\s*(?P<content>.+)$"
    )

    def __init__(
        self,
        my_username: str = "",
        message_pattern: Optional[re.Pattern] = None,
        max_history: int = 100,
        require_known_speaker: bool = False,
    ) -> None:
        self.my_username = my_username.strip().lower()
        self.pattern = message_pattern or self.DEFAULT_PATTERN
        self._seen_hashes: Deque[int] = deque(maxlen=max_history)
        self.require_known_speaker = require_known_speaker

    def reset(self) -> None:
        self._seen_hashes.clear()

    def parse(self, ocr_result: OcrResult) -> List[ParsedMessage]:
        if not ocr_result.lines:
            return []

        parsed: List[ParsedMessage] = []

        for line in ocr_result.lines:
            raw_text = line.text.strip()
            if not raw_text:
                continue

            match = self.pattern.match(raw_text)
            if match:
                speaker = match.group("speaker").strip()
                content = match.group("content").strip()
            else:
                # If format does not match colon pattern, treat full line as anonymous message
                if self.require_known_speaker:
                    continue
                speaker = "Unknown"
                content = raw_text

            is_self = bool(self.my_username and speaker.lower() == self.my_username)

            msg_hash = hash((speaker.lower(), content.strip()))
            if msg_hash in self._seen_hashes:
                continue

            self._seen_hashes.append(msg_hash)
            parsed.append(
                ParsedMessage(
                    speaker=speaker,
                    text=content,
                    is_self=is_self,
                    raw_line=raw_text,
                )
            )

        return parsed
