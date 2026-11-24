"""Phase 4 contracts for untrusted commercial firewall records.

The strict phase 1/2 NormalizedEvent remains unchanged for the historical lab.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Protocol


VENDORS = ("palo_alto", "fortinet", "sophos", "synthetic")
PARSE_STATES = ("NORMALIZED", "UNMAPPED", "REJECTED", "DUPLICATE")
ACTIONS = ("allow", "deny", "drop", "reset", "close", "other", "unknown")


def _bounded(value, label, *, required=False, limit=256):
    if value is None and not required:
        return
    if not isinstance(value, str) or (required and not value) or len(value) > limit:
        raise ValueError(f"{label} inválido")


def _time(value, label):
    if value is None:
        return
    _bounded(value, label, required=True, limit=64)
    try:
        datetime.fromisoformat(value)
    except ValueError as error:
        raise ValueError(f"{label} requiere ISO 8601") from error


@dataclass(frozen=True)
class SourceDescriptor:
    source_id: str
    vendor: str
    format_id: str
    kind: str = "synthetic_import"
    device_id: str | None = None
    declared_version: str | None = None
    enabled: bool = True

    def __post_init__(self):
        _bounded(self.source_id, "source_id", required=True, limit=128)
        _bounded(self.format_id, "format_id", required=True, limit=128)
        _bounded(self.device_id, "device_id", limit=128)
        _bounded(self.declared_version, "declared_version", limit=64)
        if self.vendor not in VENDORS or self.kind not in (
            "historical_lab", "synthetic_import", "lab_collector", "configured_unconnected"
        ) or type(self.enabled) is not bool:
            raise ValueError("Fuente no compatible")


@dataclass(frozen=True)
class FirewallEvent:
    event_id: str
    source_id: str
    vendor: str
    format_id: str
    parser_version: str
    received_at: str
    raw_reference: str
    device_id: str | None = None
    declared_version: str | None = None
    event_time: str | None = None
    timezone: str | None = None
    ingestion_batch_id: str | None = None
    action_original: str | None = None
    action: str = "unknown"
    source_ip: str | None = None
    destination_ip: str | None = None
    source_port: int | None = None
    destination_port: int | None = None
    policy_id: str | None = None
    source_zone: str | None = None
    destination_zone: str | None = None
    inbound_interface: str | None = None
    outbound_interface: str | None = None
    session_id: str | None = None
    application: str | None = None
    bytes_total: int | None = None
    bytes_sent: int | None = None
    bytes_received: int | None = None
    threat_id: str | None = None
    threat_name: str | None = None
    threat_severity: str | None = None
    original_fields: dict[str, Any] = field(default_factory=dict)
    unmapped_fields: dict[str, Any] = field(default_factory=dict)
    uncertainty: tuple[str, ...] = ()

    def __post_init__(self):
        for name in ("event_id", "source_id", "format_id", "parser_version", "raw_reference"):
            _bounded(getattr(self, name), name, required=True, limit=256)
        for name in ("device_id", "declared_version", "timezone", "ingestion_batch_id",
                     "action_original", "source_ip", "destination_ip", "policy_id", "source_zone",
                     "destination_zone", "inbound_interface", "outbound_interface", "session_id",
                     "application", "threat_id", "threat_name", "threat_severity"):
            _bounded(getattr(self, name), name)
        _time(self.received_at, "received_at")
        _time(self.event_time, "event_time")
        if self.vendor not in VENDORS or self.action not in ACTIONS:
            raise ValueError("Fabricante o acción no compatible")
        for name in ("source_port", "destination_port"):
            value = getattr(self, name)
            if value is not None and (type(value) is not int or not 0 <= value <= 65535):
                raise ValueError(f"{name} inválido")
        for name in ("bytes_total", "bytes_sent", "bytes_received"):
            value = getattr(self, name)
            if value is not None and (type(value) is not int or value < 0):
                raise ValueError(f"{name} inválido")
        if not isinstance(self.original_fields, dict) or not isinstance(self.unmapped_fields, dict):
            raise ValueError("Campos originales y no mapeados deben ser diccionarios")


@dataclass(frozen=True)
class FirewallParseResult:
    status: str
    parser_id: str
    message_id: str
    event: FirewallEvent | None = None
    errors: tuple[str, ...] = ()

    def __post_init__(self):
        if self.status not in PARSE_STATES:
            raise ValueError("Estado de parseo inválido")
        _bounded(self.parser_id, "parser_id", required=True, limit=128)
        _bounded(self.message_id, "message_id", required=True, limit=128)
        if (self.status == "NORMALIZED") != (self.event is not None):
            raise ValueError("NORMALIZED requiere evento; otros estados no")
        if self.status in ("REJECTED", "UNMAPPED") and not self.errors:
            raise ValueError("Resultado no normalizado requiere explicación")


class ModelProvider(Protocol):
    provider_id: str

    def generate(self, prompt: str, evidence: tuple, limits: Any) -> Any: ...


class AgentRuntime(Protocol):
    def investigate(self, alert_id: str, *, mode: str = "deterministic") -> dict: ...
