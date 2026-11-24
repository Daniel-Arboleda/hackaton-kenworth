"""Explicit, credential-free local model selection for the existing orchestrator."""

from kenworth.assistant_providers import ConfiguredProvider, LocalHTTPTransport, OllamaTransport, ProviderSettings


def local_provider(enabled=False, endpoint="", model_id=""):
    """Return an opt-in loopback adapter or None for deterministic fallback."""
    if not enabled:
        return None
    if not model_id or len(model_id) > 120 or any(c in model_id for c in "\r\n"):
        raise ValueError("Identificador de modelo local inválido")
    transport = LocalHTTPTransport(endpoint)
    return ConfiguredProvider(ProviderSettings("local", enabled=True, model_id=model_id), transport)


def ollama_provider(enabled=False, endpoint="http://127.0.0.1:11434/api/generate", model_id=""):
    """Opt-in real Ollama protocol; no model download or network outside loopback."""
    if not enabled:
        return None
    if not model_id or len(model_id) > 120 or any(c in model_id for c in "\r\n"):
        raise ValueError("Identificador de modelo Ollama inválido")
    return ConfiguredProvider(ProviderSettings("ollama", enabled=True, model_id=model_id),
                              OllamaTransport(endpoint))
