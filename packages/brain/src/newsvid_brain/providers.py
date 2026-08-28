from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Any, Callable, Protocol

import httpx

from .errors import LLMError, StructuredOutputError


class LLMProvider(Protocol):
    @property
    def cache_key(self) -> str: ...

    def generate_structured(self, prompt: str, schema: dict[str, Any]) -> dict[str, Any]: ...


@dataclass(frozen=True)
class OllamaConfig:
    base_url: str = "http://127.0.0.1:11434"
    model: str = "qwen2.5:7b"
    temperature: float = 0.1
    timeout_seconds: float = 120
    max_attempts: int = 3
    base_delay_seconds: float = 0.25


class OllamaProvider:
    """Ollama native structured output behind the project LLM boundary."""

    _retry_statuses = {429, 500, 502, 503, 504}
    _retry_errors = (httpx.ConnectError, httpx.ConnectTimeout, httpx.ReadTimeout,
                     httpx.WriteTimeout, httpx.PoolTimeout)

    def __init__(self, config: OllamaConfig, *, transport: httpx.BaseTransport | None = None,
                 sleeper: Callable[[float], None] = time.sleep) -> None:
        self.config = config
        self._transport = transport
        self._sleeper = sleeper

    @property
    def cache_key(self) -> str:
        return f"ollama:{self.config.base_url.rstrip('/')}:{self.config.model}:t={self.config.temperature}"

    def generate_structured(self, prompt: str, schema: dict[str, Any]) -> dict[str, Any]:
        endpoint = f"{self.config.base_url.rstrip('/')}/api/chat"
        payload = {"model": self.config.model, "stream": False, "format": schema,
                   "options": {"temperature": self.config.temperature},
                   "messages": [{"role": "user", "content": prompt}]}
        last_error: Exception | None = None
        for attempt in range(1, self.config.max_attempts + 1):
            try:
                with httpx.Client(timeout=self.config.timeout_seconds, transport=self._transport) as client:
                    response = client.post(endpoint, json=payload)
                    response.raise_for_status()
                envelope = response.json()
                content = envelope["message"]["content"]
                if not isinstance(content, str):
                    raise StructuredOutputError("Ollama response content must be text")
                result = json.loads(content.strip())
                if not isinstance(result, dict):
                    raise StructuredOutputError("Ollama structured output must be a JSON object")
                return result
            except (json.JSONDecodeError, KeyError, TypeError) as exc:
                raise StructuredOutputError("Ollama returned invalid structured output") from exc
            except StructuredOutputError:
                raise
            except httpx.HTTPStatusError as exc:
                last_error = exc
                if exc.response.status_code not in self._retry_statuses or attempt == self.config.max_attempts:
                    break
            except self._retry_errors as exc:
                last_error = exc
                if attempt == self.config.max_attempts:
                    break
            if attempt < self.config.max_attempts:
                self._sleeper(self.config.base_delay_seconds * (2 ** (attempt - 1)))
        raise LLMError(f"Ollama request failed after {self.config.max_attempts} attempt(s)") from last_error
