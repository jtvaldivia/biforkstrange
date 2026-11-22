"""Cliente de Claude que devuelve JSON validado con Pydantic (structured outputs + un reintento).

Las credenciales, el cliente y la traducción de errores son los de `claude_comun`, los mismos que usan
la lectura del perfil y el narrador.
"""

import json
import re
from collections.abc import Callable
from functools import lru_cache
from typing import TypeVar

from pydantic import BaseModel, ValidationError

from app.core.config import get_settings
from app.services import claude_comun

T = TypeVar("T", bound=BaseModel)

ESPERA_MAX = 90  # segundos por intento: el informe (esfuerzo medio, hasta 12 mil tokens) es lo más lento
FALLBACK_BETA = "server-side-fallback-2026-07-01"
# Modelos donde se puede apagar el razonamiento previo (más rápido). En Opus/Sonnet 5.5 apagarlo da 400.
NO_THINKING_PREFIXES = ("claude-haiku-5",)
# Modelos que aceptan el reintento del servidor cuando un clasificador rechaza (Haiku no lo tiene)
FALLBACK_MODELS = {"claude-fable-5-2", "claude-fable-5-1", "claude-opus-5-5", "claude-opus-5", "claude-sonnet-5-5"}


class LLMError(claude_comun.ClaudeNoDisponible):
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
    def __init__(self, client, model: str):
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
        """`fast` apaga el razonamiento previo en los modelos que lo permiten (respuesta más rápida).

        Si la respuesta no pasa la validación o `check`, se reintenta una vez diciéndole al modelo qué falló."""
        schema = strict_schema(out)
        extra: dict = {}
        if self.model in FALLBACK_MODELS:
            # si un clasificador rechaza, el servidor reintenta en el modelo que corresponda
            extra = {"betas": [FALLBACK_BETA], "fallbacks": "default"}
        if fast and self.model.startswith(NO_THINKING_PREFIXES):
            extra["thinking"] = {"type": "disabled"}
        texto = prompt
        last_err: Exception | None = None
        for _ in range(2):
            try:
                resp = self.client.beta.messages.create(
                    model=self.model,
                    max_tokens=max_tokens,
                    output_config={"effort": effort, "format": {"type": "json_schema", "schema": schema}},
                    messages=[{"role": "user", "content": texto}],
                    **extra,
                )
            except claude_comun.ERRORES_API as e:
                raise claude_comun.traducir_error(e, LLMError) from e

            if resp.stop_reason == "refusal":
                raise LLMError("Claude declinó generar esta respuesta.")
            if resp.stop_reason == "max_tokens":
                last_err = ValueError("la respuesta quedó cortada; sé más breve")
            else:
                text = "".join(b.text for b in resp.content if b.type == "text")
                try:
                    parsed = out.model_validate(json.loads(extract_json(text)))
                    if check:
                        check(parsed)
                    return parsed
                except (ValueError, ValidationError) as e:
                    last_err = e
            texto = f"{prompt}\n\nTu respuesta anterior no sirvió: {str(last_err)[:500]}. Corrígela."
        raise LLMError(f"Respuesta inválida del modelo: {last_err}")


@lru_cache
def get_claude(model: str | None = None) -> ClaudeJSON:
    return ClaudeJSON(claude_comun.cliente(ESPERA_MAX, max_retries=1), model or get_settings().anthropic_model)
