from __future__ import annotations

import json
import unittest
from autochat.engine.providers import OllamaProvider, SyrinPoolProvider


class DummyTransport:
    def __init__(self, response_dict: dict) -> None:
        self.response_dict = response_dict
        self.last_url = ""
        self.last_body = b""
        self.last_headers = {}

    def post_json(self, url: str, payload: dict, timeout: float = 10.0) -> dict:
        self.last_url = url
        self.last_body = json.dumps(payload).encode("utf-8")
        return self.response_dict


class ProviderTests(unittest.TestCase):
    def test_ollama_provider_request_format(self) -> None:
        mock_response = {
            "model": "qwen2.5:3b",
            "response": "Đang chạy tới cứu bồ đây!",
            "done": True,
        }
        transport = DummyTransport(mock_response)
        provider = OllamaProvider(
            endpoint="http://localhost:11434",
            model="qwen2.5:3b",
            transport=transport,
        )

        reply = provider.generate("Cứu bot gấp!")
        self.assertEqual(reply, "Đang chạy tới cứu bồ đây!")
        self.assertEqual(transport.last_url, "http://localhost:11434/api/generate")

    def test_syrin_pool_provider_request_format(self) -> None:
        mock_response = {
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": "Bình tĩnh, giữ trụ chờ đồng đội.",
                    }
                }
            ]
        }
        transport = DummyTransport(mock_response)
        provider = SyrinPoolProvider(
            endpoint="http://localhost:9100",
            model="gpt-5.4",
            transport=transport,
        )

        reply = provider.generate("Team kia ép gắt quá")
        self.assertEqual(reply, "Bình tĩnh, giữ trụ chờ đồng đội.")
        self.assertEqual(transport.last_url, "http://localhost:9100/v1/chat/completions")


if __name__ == "__main__":
    unittest.main()
