"""Cliente de Claude que devuelve JSON validado con Pydantic (structured outputs + un reintento)."""

import json
import re
from collections.abc import Callable
from functools import lru_cache
from typing import TypeVar

import anthropic
from pydantic import BaseModel, ValidationError

from app.core.config import get_settings

T = TypeVar("T", bound=BaseModel)

FALLBACK_BETA = "server-side-fallback-2026-07-01"
# Modelos donde se puede apagar el razonamiento previo (más rápido). En Opus/Sonnet 5.5 apagarlo da 400.
NO_THINKING_PREFIXES = ("claude-haiku-5",)
# Modelos que aceptan el reintento del servidor cuando un clasificador rechaza (Haiku no lo tiene)
FALLBACK_MODELS = {"claude-fable-5-2", "claude-fable-5-1", "claude-opus-5-5", "claude-opus-5", "claude-sonnet-5-5"}


class LLMError(Exception):
    """El modelo no respondió algo usable (red, rechazo o JSON inválido dos veces)."""


def strict_schema(model: type[BaseModel]) -> dict:
    """Schema de Pydantic con additionalProperties=false en cada objeto, como pide structured outputs."""
    schema = model.model_json_schema()

    def walk(node):
        if isinstance(node, dict):
            if node.get("type") == "object" and "properties" in node:
                node["additionalProperties"] = False
                node["required"] = list(node["properties"])
            for v in node.values():
                walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)

    walk(schema)
    return schema


def extract_json(text: str) -> str:
    """Primer objeto {...} del texto (por si viene envuelto en algo más)."""
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if not m:
        raise ValueError("No hay JSON en la respuesta")
    return m.group(0)


class ClaudeJSON:
    def __init__(self, client: anthropic.Anthropic, model: str):
        self.client = client
        self.model = model

    def ask(
        self,
        prompt: str,
        out: type[T],
        *,
        effort: str = "low",
        max_tokens: int = 8000,
        check: Callable[[T], None] | None = None,
        fast: bool = False,
    ) -> T:
        """`fast` apaga el razonamiento previo en los modelos que lo permiten (respuesta más rápida)."""
        schema = strict_schema(out)
        last_err: Exception | None = None
        for _ in range(2):  # un reintento si el JSON no pasa la validación
            try:
                extra = {}
                if self.model in FALLBACK_MODELS:
                    # si un clasificador rechaza, el servidor reintenta en el modelo que corresponda
                    extra = {"betas": [FALLBACK_BETA], "fallbacks": "default"}
                if fast and self.model.startswith(NO_THINKING_PREFIXES):
                    extra["thinking"] = {"type": "disabled"}
                resp = self.client.beta.messages.create(
                    model=self.model,
                    max_tokens=max_tokens,
                    output_config={"effort": effort, "format": {"type": "json_schema", "schema": schema}},
                    messages=[{"role": "user", "content": prompt}],
                    **extra,
                )
            except anthropic.RateLimitError as e:
                raise LLMError("Claude está con mucha carga (rate limit). Intenta en un rato.") from e
            except anthropic.AuthenticationError as e:
                raise LLMError("ANTHROPIC_API_KEY inválida.") from e
            except anthropic.APIStatusError as e:
                raise LLMError(f"Error de la API de Claude ({e.status_code}): {e.message}") from e
            except anthropic.APIConnectionError as e:
                raise LLMError("No se pudo conectar con la API de Claude.") from e

            if resp.stop_reason == "refusal":
                raise LLMError("Claude declinó generar esta respuesta.")
            if resp.stop_reason == "max_tokens":
                last_err = ValueError("Respuesta cortada por max_tokens")
                continue

            text = "".join(b.text for b in resp.content if b.type == "text")
            try:
                parsed = out.model_validate(json.loads(extract_json(text)))
                if check:
                    check(parsed)
                return parsed
            except (ValueError, ValidationError) as e:
                last_err = e
        raise LLMError(f"Respuesta inválida del modelo: {last_err}")


@lru_cache
def get_claude(model: str | None = None) -> ClaudeJSON:
    s = get_settings()
    return ClaudeJSON(anthropic.Anthropic(api_key=s.anthropic_api_key or None), model or s.anthropic_model)
