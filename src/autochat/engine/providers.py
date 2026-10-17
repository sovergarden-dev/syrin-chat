from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any, Dict, Optional


class UrllibTransport:
    """Zero-dependency HTTP transport using Python standard library urllib."""

    def post_json(self, url: str, payload: Dict[str, Any], timeout: float = 10.0) -> Dict[str, Any]:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={
                "Content-Type": "application/json",
                "User-Agent": "AutoChatAgent/0.1.0",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
            return json.loads(raw.decode("utf-8"))


class OllamaProvider:
    """Connects to local Ollama daemon (default localhost:11434)."""

    def __init__(
        self,
        endpoint: str = "http://localhost:11434",
        model: str = "qwen2.5:3b",
        transport: Optional[Any] = None,
        timeout: float = 15.0,
    ) -> None:
        self.endpoint = endpoint.rstrip("/")
        self.model = model
        self.transport = transport or UrllibTransport()
        self.timeout = timeout

    def generate(self, prompt: str) -> str:
        url = f"{self.endpoint}/api/generate"
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
        }
        try:
            resp = self.transport.post_json(url, payload, timeout=self.timeout)
            return resp.get("response", "").strip()
        except Exception:
            return ""


class SyrinPoolProvider:
    """Connects to local Syrin Pool proxy (default localhost:9100) using OpenAI-compatible format."""

    def __init__(
        self,
        endpoint: str = "http://localhost:9100",
        model: str = "gpt-5.4",
        transport: Optional[Any] = None,
        timeout: float = 20.0,
    ) -> None:
        self.endpoint = endpoint.rstrip("/")
        self.model = model
        self.transport = transport or UrllibTransport()
        self.timeout = timeout

    def generate(self, prompt: str) -> str:
        url = f"{self.endpoint}/v1/chat/completions"
        payload = {
            "model": self.model,
            "messages": [
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.3,
        }
        try:
            resp = self.transport.post_json(url, payload, timeout=self.timeout)
            choices = resp.get("choices", [])
            if choices and "message" in choices[0]:
                return choices[0]["message"].get("content", "").strip()
            return ""
        except Exception:
            return ""
