"""Provider adapters with a deterministic default and explicit transport gates."""

from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeout
from dataclasses import dataclass, field
from http.client import HTTPConnection
import json
import math
import re
from urllib.parse import urlsplit

from kenworth.contracts_v2 import AssistantResponse


PROVIDER_IDS = ('fallback', 'local', 'openai', 'anthropic', 'deepseek')
_EXTERNAL = {'openai', 'anthropic', 'deepseek'}
_IP = re.compile(r'(?<![\d.])(?:\d{1,3}\.){3}\d{1,3}(?![\d.])')
_EMAIL = re.compile(r'\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}\b')
_USER_FIELD = re.compile(r'("(?:usuario_prueba|responsable|justificacion)"\s*:\s*)"(?:[^"\\]|\\.)*"')


class ProviderUnavailable(RuntimeError):
    """A provider was disabled, over budget, late or returned invalid output."""


class LocalHTTPTransport:
    """Small loopback-only JSON transport; no redirects or arbitrary URLs."""

    def __init__(self, endpoint):
        parsed = urlsplit(endpoint)
        if (parsed.scheme != 'http' or parsed.hostname not in ('127.0.0.1', 'localhost', '::1')
                or parsed.port is None or parsed.path != '/generate'
                or parsed.query or parsed.fragment or parsed.username or parsed.password):
            raise ValueError('El proveedor local exige http://loopback:puerto/generate')
        self.host = parsed.hostname
        self.port = parsed.port

    def __call__(self, request, timeout_seconds, api_key):
        if request['provider_id'] != 'local' or api_key:
            raise ValueError('Transporte exclusivo para proveedor local sin credenciales')
        connection = HTTPConnection(self.host, self.port, timeout=timeout_seconds)
        try:
            body = json.dumps({'model': request['model_id'], 'prompt': request['prompt'],
                               'max_output_chars': request['max_output_chars']},
                              ensure_ascii=False).encode('utf-8')
            connection.request('POST', '/generate', body=body,
                               headers={'Content-Type': 'application/json'})
            response = connection.getresponse()
            if response.status != 200:
                raise ProviderUnavailable(f'Servidor local respondió HTTP {response.status}')
            data = response.read(request['max_output_chars'] * 4 + 1024)
            if len(data) > request['max_output_chars'] * 4 + 1023:
                raise ProviderUnavailable('Respuesta local excede límite de bytes')
            payload = json.loads(data.decode('utf-8'))
            if not isinstance(payload, dict) or not isinstance(payload.get('text'), str):
                raise ProviderUnavailable('Respuesta local requiere objeto JSON con text')
            return payload['text']
        finally:
            connection.close()


def redact_for_external(text):
    """Mask common identifiers; caller must still explicitly opt in to transfer."""
    text = _IP.sub('[IP_REDACTADA]', text)
    text = _EMAIL.sub('[EMAIL_REDACTADO]', text)
    return _USER_FIELD.sub(r'\1"[REDACTADO]"', text)


@dataclass(frozen=True)
class ProviderSettings:
    provider_id: str
    enabled: bool = False
    allow_external_data: bool = False
    model_id: str = ''
    api_key: str = field(default='', repr=False)
    max_estimated_usd: float = 0.0
    estimated_usd_per_1000_tokens: float = 0.0

    def __post_init__(self):
        if self.provider_id not in PROVIDER_IDS[1:]:
            raise ValueError('Proveedor desconocido')
        if (not math.isfinite(self.max_estimated_usd)
                or not math.isfinite(self.estimated_usd_per_1000_tokens)
                or self.max_estimated_usd < 0 or self.estimated_usd_per_1000_tokens < 0):
            raise ValueError('Límites de costo inválidos')


class DeterministicProvider:
    provider_id = 'fallback'
    is_external = False

    def generate(self, question, evidence, limits):
        try:
            payload = json.loads(question)
        except json.JSONDecodeError as error:
            raise ProviderUnavailable('Contexto estructurado inválido') from error
        alert = payload.get('alert') or {}
        explanation = payload.get('explanation') or {}
        text = (f"Borrador para {alert.get('alerta_id', 'alerta no identificada')} "
                f"(evento {alert.get('evento_id', 'no identificado')}): "
                f"{explanation.get('interpretacion_prudente', 'Revisar evidencia disponible.')} "
                f"Siguiente verificación: {explanation.get('siguiente_paso', 'Consultar al analista.')} "
                "No confirma incidente ni ejecuta contención; requiere revisión humana.")
        return AssistantResponse(text=text[:limits.max_output_chars], evidence=evidence,
                                 status='FALLBACK')


class ConfiguredProvider:
    """Local or vendor adapter; network transport is injected, never implicit."""

    def __init__(self, settings, transport=None):
        if settings.provider_id not in PROVIDER_IDS[1:]:
            raise ValueError('Proveedor desconocido')
        self.settings = settings
        self.provider_id = settings.provider_id
        self.is_external = self.provider_id in _EXTERNAL
        self._transport = transport

    def generate(self, question, evidence, limits):
        if not self.settings.enabled or self._transport is None:
            raise ProviderUnavailable('Proveedor deshabilitado o sin transporte configurado')
        if self.is_external and (not self.settings.allow_external_data or not self.settings.api_key):
            raise ProviderUnavailable('Transferencia externa no habilitada o credencial ausente')
        prompt = redact_for_external(question) if self.is_external else question
        if len(prompt) > limits.max_context_chars:
            raise ProviderUnavailable('Contexto excede límite de caracteres')
        estimated_tokens = math.ceil(len(prompt) / 4) + math.ceil(limits.max_output_chars / 4)
        estimated_usd = estimated_tokens * self.settings.estimated_usd_per_1000_tokens / 1000
        if self.is_external and (self.settings.estimated_usd_per_1000_tokens <= 0
                                 or self.settings.max_estimated_usd <= 0
                                 or estimated_usd > self.settings.max_estimated_usd):
            raise ProviderUnavailable('Presupuesto estimado no configurado o excedido')
        request = dict(provider_id=self.provider_id, model_id=self.settings.model_id,
                       prompt=prompt, max_output_chars=limits.max_output_chars,
                       max_estimated_usd=self.settings.max_estimated_usd)
        # The caller's transport must implement its own network timeout too.
        executor = ThreadPoolExecutor(max_workers=1)
        try:
            future = executor.submit(self._transport, request, limits.timeout_seconds,
                                     self.settings.api_key if self.is_external else '')
            result = future.result(timeout=limits.timeout_seconds)
        except FutureTimeout as error:
            raise ProviderUnavailable('Proveedor excedió tiempo límite') from error
        except Exception as error:
            raise ProviderUnavailable(f'Proveedor falló: {type(error).__name__}') from error
        finally:
            executor.shutdown(wait=False, cancel_futures=True)
        if not isinstance(result, str) or not result.strip() or len(result) > limits.max_output_chars:
            raise ProviderUnavailable('Respuesta vacía o fuera de límite')
        return AssistantResponse(text=result, evidence=evidence, status='DRAFT')
