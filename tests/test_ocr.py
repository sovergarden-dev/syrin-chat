from __future__ import annotations

import unittest
from autochat.perception.frame import Frame
from autochat.perception.ocr import (
    MockOcrBackend,
    OcrBackend,
    OcrLine,
    OcrResult,
    OcrWord,
)
from autochat.ui.geometry import Rect


class OcrTests(unittest.TestCase):
    def test_ocr_data_structures(self) -> None:
        w1 = OcrWord(text="Xin", bounding_box=Rect(0, 0, 30, 20), confidence=0.99)
        w2 = OcrWord(text="chào", bounding_box=Rect(35, 0, 45, 20), confidence=0.98)
        line = OcrLine(
            text="Xin chào",
            words=[w1, w2],
            bounding_box=Rect(0, 0, 80, 20),
            confidence=0.985,
        )
        res = OcrResult(lines=[line], full_text="Xin chào")

        self.assertEqual(len(res.lines), 1)
        self.assertEqual(res.lines[0].text, "Xin chào")
        self.assertEqual(res.full_text, "Xin chào")

    def test_mock_ocr_backend(self) -> None:
        w = OcrWord(text="Test", bounding_box=Rect(0, 0, 40, 20), confidence=1.0)
        line = OcrLine(text="Test", words=[w], bounding_box=Rect(0, 0, 40, 20), confidence=1.0)
        mock_result = OcrResult(lines=[line], full_text="Test")

        backend = MockOcrBackend(default_result=mock_result)
        self.assertIsInstance(backend, OcrBackend)

        frame = Frame(10, 10, 1, bytes([0] * 100))
        result = backend.recognize(frame)
        self.assertEqual(result.full_text, "Test")
        self.assertEqual(len(result.lines), 1)

    def test_mock_ocr_backend_empty(self) -> None:
        backend = MockOcrBackend()
        frame = Frame(10, 10, 1, bytes([0] * 100))
        result = backend.recognize(frame)
        self.assertEqual(result.full_text, "")
        self.assertEqual(len(result.lines), 0)


if __name__ == "__main__":
    unittest.main()
