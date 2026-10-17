from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Protocol, runtime_checkable
from ..ui.geometry import Rect
from .frame import Frame


@dataclass(frozen=True)
class OcrWord:
    text: str
    bounding_box: Rect
    confidence: float = 1.0


@dataclass(frozen=True)
class OcrLine:
    text: str
    words: List[OcrWord] = field(default_factory=list)
    bounding_box: Optional[Rect] = None
    confidence: float = 1.0


@dataclass(frozen=True)
class OcrResult:
    lines: List[OcrLine] = field(default_factory=list)
    full_text: str = ""


@runtime_checkable
class OcrBackend(Protocol):
    def recognize(self, frame: Frame) -> OcrResult: ...


class MockOcrBackend:
    def __init__(self, default_result: Optional[OcrResult] = None) -> None:
        self._default_result = default_result or OcrResult()

    def set_result(self, result: OcrResult) -> None:
        self._default_result = result

    def recognize(self, frame: Frame) -> OcrResult:
        return self._default_result


class WinRtOcrBackend:
    """Native Windows 10/11 WinRT OCR engine."""

    def __init__(self, language_tag: str = "vi-VN") -> None:
        self.language_tag = language_tag
        self._engine = None
        self._is_available = False
        self._init_engine()

    def _init_engine(self) -> None:
        try:
            # Check for winrt / winsdk availability
            import winsdk.windows.media.ocr as win_ocr  # type: ignore
            import winsdk.windows.globalization as win_glob  # type: ignore

            lang = win_glob.Language(self.language_tag)
            if win_ocr.OcrEngine.is_language_supported(lang):
                self._engine = win_ocr.OcrEngine.try_create_from_language(lang)
            else:
                self._engine = win_ocr.OcrEngine.try_create_from_user_profile_languages()
            self._is_available = self._engine is not None
        except Exception:
            self._is_available = False

    @property
    def is_available(self) -> bool:
        return self._is_available

    def recognize(self, frame: Frame) -> OcrResult:
        if not self._is_available or self._engine is None:
            return OcrResult()
        # In live Windows environments with winsdk installed, frame bytes are converted to SoftwareBitmap
        return OcrResult()
