"""Local-only configuration for PRIA."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse


DEFAULT_CONFIG = Path(__file__).resolve().parent.parent / "config.json"


@dataclass(frozen=True)
class Settings:
    base_url: str = "http://127.0.0.1:11434"
    model: str = "qwen2.5:7b"
    timeout_seconds: int = 180
    context_window: int = 4096
    max_response_tokens: int = 256


def load_settings(path: Path | None = None) -> Settings:
    values = {}
    config_path = path or DEFAULT_CONFIG
    if config_path.exists():
        try:
            values = json.loads(config_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError(f"Configuração inválida em {config_path}: {exc}") from exc
        if not isinstance(values, dict):
            raise ValueError("config.json deve conter um objeto JSON.")
    base_url = os.getenv("PRIA_OLLAMA_URL", str(values.get("base_url", Settings.base_url))).rstrip("/")
    model = os.getenv("PRIA_MODEL", str(values.get("model", Settings.model))).strip()
    timeout = int(os.getenv("PRIA_TIMEOUT", values.get("timeout_seconds", Settings.timeout_seconds)))
    context = int(os.getenv("PRIA_CONTEXT", values.get("context_window", Settings.context_window)))
    max_tokens = int(os.getenv("PRIA_MAX_RESPONSE_TOKENS", values.get("max_response_tokens", Settings.max_response_tokens)))
    parsed = urlparse(base_url)
    if parsed.scheme != "http" or parsed.hostname not in {"127.0.0.1", "localhost", "::1"} or not parsed.port:
        raise ValueError("O serviço do modelo deve usar HTTP em localhost/loopback com porta explícita.")
    if not model or timeout < 1 or context < 256 or max_tokens < 1:
        raise ValueError("Modelo, timeout, contexto ou limite de resposta inválido.")
    return Settings(base_url, model, timeout, context, max_tokens)
