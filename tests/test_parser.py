from __future__ import annotations

import unittest
from autochat.perception.ocr import OcrLine, OcrResult
from autochat.perception.parser import ParsedMessage, TranscriptParser


class TranscriptParserTests(unittest.TestCase):
    def setUp(self) -> None:
        self.parser = TranscriptParser(my_username="MyBotPlayer")

    def test_parse_standard_colon_message(self) -> None:
        line = OcrLine(text="Player1: Cứu tao với bồ ơi")
        result = OcrResult(lines=[line], full_text=line.text)

        messages = self.parser.parse(result)
        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0].speaker, "Player1")
        self.assertEqual(messages[0].text, "Cứu tao với bồ ơi")
        self.assertFalse(messages[0].is_self)

    def test_detect_self_message(self) -> None:
        line = OcrLine(text="mybotplayer: Đang đến đây")
        result = OcrResult(lines=[line], full_text=line.text)

        messages = self.parser.parse(result)
        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0].speaker, "mybotplayer")
        self.assertEqual(messages[0].text, "Đang đến đây")
        self.assertTrue(messages[0].is_self)

    def test_parse_with_timestamp_prefix(self) -> None:
        line = OcrLine(text="[12:34] TeammateA: Đẩy mid đi")
        result = OcrResult(lines=[line], full_text=line.text)

        messages = self.parser.parse(result)
        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0].speaker, "TeammateA")
        self.assertEqual(messages[0].text, "Đẩy mid đi")
        self.assertFalse(messages[0].is_self)

    def test_deduplicate_identical_messages(self) -> None:
        line = OcrLine(text="Player1: Hello world")
        result = OcrResult(lines=[line], full_text=line.text)

        # First parse returns 1 message
        m1 = self.parser.parse(result)
        self.assertEqual(len(m1), 1)

        # Second parse of identical OCR returns 0 new messages
        m2 = self.parser.parse(result)
        self.assertEqual(len(m2), 0)

    def test_require_known_speaker_filters_anonymous(self) -> None:
        parser = TranscriptParser(my_username="MyBotPlayer", require_known_speaker=True)
        line = OcrLine(text="Random chat without colon delimiter")
        result = OcrResult(lines=[line], full_text=line.text)

        messages = parser.parse(result)
        self.assertEqual(len(messages), 0)


if __name__ == "__main__":
    unittest.main()
