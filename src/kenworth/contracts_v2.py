"""Phase 2 wire contracts; no collection, approval or AI execution lives here."""

from dataclasses import asdict, dataclass, field, is_dataclass
from datetime import datetime
import json
import re
from typing import Any, Iterator, Literal, Protocol

from kenworth.ingestion import FIELDS


MAX_MESSAGE_CHARS = 65_536
AUDIT_STATES = (
    "BORRADOR", "EVALUADA", "PROPUESTA", "VALIDADA", "APROBADA",
    "APLICADA_LOCALMENTE", "RECHAZADA",
)
PARSE_STATES = ("NORMALIZED", "REJECTED", "UNMAPPED")
SOURCE_STATES = ("ARCHIVE", "LISTENING", "DEGRADED", "STOPPED")
_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")


def _identifier(value: str, label: str) -> None:
    if not isinstance(value, str) or not _ID.fullmatch(value):
        raise ValueError(f"{label} debe ser un identificador no vacío y acotado")


def _timestamp(value: str, label: str) -> None:
    if not isinstance(value, str):
        raise ValueError(f"{label} debe ser ISO 8601")
    try:
        datetime.fromisoformat(value)
    except ValueError as error:
        raise ValueError(f"{label} debe ser ISO 8601") from error


def to_json_dict(record: Any) -> dict:
    """Reject non-JSON payloads instead of silently stringifying evidence."""
    if not is_dataclass(record) or isinstance(record, type):
        raise TypeError("Se requiere una instancia de contrato dataclass")
    data = asdict(record)
    json.dumps(data, allow_nan=False, ensure_ascii=False)
    return data


@dataclass(frozen=True)
class SourceMessage:
    source_id: str
    message_id: str
    received_at: str
    raw: str

    def __post_init__(self):
        _identifier(self.source_id, "source_id")
        _identifier(self.message_id, "message_id")
        _timestamp(self.received_at, "received_at")
        if not isinstance(self.raw, str) or not 0 < len(self.raw) <= MAX_MESSAGE_CHARS:
            raise ValueError("raw debe tener 1 a 65536 caracteres")


@dataclass(frozen=True)
class SourceHealth:
    source_id: str
    state: str
    last_received_at: str | None = None
    accepted: int = 0
    rejected: int = 0
    detail: str = ""

    def __post_init__(self):
        _identifier(self.source_id, "source_id")
        if self.state not in SOURCE_STATES:
            raise ValueError("Estado de fuente no permitido")
        if self.last_received_at is not None:
            _timestamp(self.last_received_at, "last_received_at")
        if any(type(value) is not int or value < 0 for value in (self.accepted, self.rejected)):
            raise ValueError("Los contadores de fuente deben ser enteros no negativos")


class EventSource(Protocol):
    """Bounded source; implementations must not expose unrestricted network targets."""

    source_id: str
    kind: str

    def health(self) -> SourceHealth: ...

    def iter_messages(self, limit: int) -> Iterator[SourceMessage]: ...


@dataclass(frozen=True)
class NormalizedEvent:
    """Canonical phase 1 fields plus optional phase 2 provenance."""

    evento_id: str
    fecha_hora: str
    zona_horaria: str
    tipo: str
    origen_ip: str
    destino_ip: str
    puerto_destino: str
    accion: str
    regla_id: str
    usuario_prueba: str
    resultado: str
    bytes: str
    source_id: str = "archive"
    parser_id: str = "canonical_csv"
    parser_version: str = "1"
    raw_fields: dict[str, Any] = field(default_factory=dict)
    unmapped_fields: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        _identifier(self.evento_id, "evento_id")
        _timestamp(self.fecha_hora, "fecha_hora")
        if self.zona_horaria != "America/Bogota":
            raise ValueError("zona_horaria debe ser America/Bogota en el contrato canónico actual")
        if self.tipo not in ("trafico", "autenticacion") or self.accion not in ("allow", "deny"):
            raise ValueError("tipo o accion no compatible con el contrato canónico")
        try:
            port, volume = int(self.puerto_destino), int(self.bytes)
        except (ValueError, TypeError) as error:
            raise ValueError("puerto_destino y bytes deben ser números enteros") from error
        if not 0 <= port <= 65535 or volume < 0:
            raise ValueError("Puerto o bytes fuera de rango")
        for name in FIELDS:
            if not isinstance(getattr(self, name), str) or not getattr(self, name):
                raise ValueError(f"Campo canónico vacío: {name}")
        for name in ("source_id", "parser_id", "parser_version"):
            _identifier(getattr(self, name), name)
        to_json_dict(self)

    @classmethod
    def from_legacy(cls, row: dict[str, str], **provenance):
        """Adapt an existing CSV row without modifying phase 1 APIs."""
        return cls(**{name: row[name] for name in FIELDS}, **provenance)

    def to_legacy_dict(self) -> dict[str, str]:
        return {name: getattr(self, name) for name in FIELDS}


@dataclass(frozen=True)
class FormatMatch:
    parser_id: str
    matched: bool
    criteria: tuple[str, ...] = ()

    def __post_init__(self):
        _identifier(self.parser_id, "parser_id")
        if type(self.matched) is not bool or (self.matched and not self.criteria):
            raise ValueError("Una coincidencia requiere criterios descriptivos")


@dataclass(frozen=True)
class ParseResult:
    status: str
    parser_id: str
    message_id: str
    event: NormalizedEvent | None = None
    errors: tuple[str, ...] = ()
    raw_fields: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if self.status not in PARSE_STATES:
            raise ValueError("Estado de parseo no permitido")
        _identifier(self.parser_id, "parser_id")
        _identifier(self.message_id, "message_id")
        if (self.status == "NORMALIZED") != (self.event is not None):
            raise ValueError("NORMALIZED requiere evento; otros estados no lo contienen")
        if self.status != "NORMALIZED" and not self.errors:
            raise ValueError("Un rechazo o formato desconocido requiere explicación")
        to_json_dict(self)


class LogParser(Protocol):
    parser_id: str
    version: str

    def identify(self, message: SourceMessage) -> FormatMatch: ...

    def parse(self, message: SourceMessage) -> ParseResult: ...


@dataclass(frozen=True)
class EvidenceRef:
    source: str
    record_id: str
    field: str = ""

    def __post_init__(self):
        _identifier(self.record_id, "record_id")
        if not isinstance(self.source, str) or not self.source.strip():
            raise ValueError("La evidencia requiere fuente")


@dataclass(frozen=True)
class AuditDefinition:
    audit_id: str
    kind: str
    version: int
    objective: str
    questions: tuple[str, ...]
    required_evidence: tuple[str, ...]
    criteria: tuple[str, ...]
    owner_role: str

    def __post_init__(self):
        _identifier(self.audit_id, "audit_id")
        if type(self.version) is not int or self.version < 1:
            raise ValueError("La versión de auditoría debe ser positiva")
        if not all((self.kind, self.objective, self.questions, self.criteria, self.owner_role)):
            raise ValueError("Definición de auditoría incompleta")
        to_json_dict(self)


@dataclass(frozen=True)
class LaboratoryApproval:
    actor_id: str
    recorded_at: str
    note: str
    mode: Literal["LAB_ONLY"] = "LAB_ONLY"

    def __post_init__(self):
        _identifier(self.actor_id, "actor_id")
        _timestamp(self.recorded_at, "recorded_at")
        if not self.note.strip() or self.mode != "LAB_ONLY":
            raise ValueError("Solo se registra aprobación identificada de laboratorio")


@dataclass(frozen=True)
class AuditFinding:
    finding_id: str
    audit_id: str
    summary: str
    evidence: tuple[EvidenceRef, ...]
    status: str = "BORRADOR"
    responsible_role: str = "Por asignar"
    evaluated_at: str | None = None
    limitations: tuple[str, ...] = ()
    version: int = 1
    approval: LaboratoryApproval | None = None

    def __post_init__(self):
        _identifier(self.finding_id, "finding_id")
        _identifier(self.audit_id, "audit_id")
        if self.status not in AUDIT_STATES or not self.summary.strip():
            raise ValueError("Hallazgo incompleto o estado inválido")
        if self.evaluated_at is not None:
            _timestamp(self.evaluated_at, "evaluated_at")
        if type(self.version) is not int or self.version < 1:
            raise ValueError("La versión debe ser positiva")
        if self.status in ("APROBADA", "APLICADA_LOCALMENTE") and self.approval is None:
            raise ValueError("Aprobación identificada de laboratorio requerida")
        to_json_dict(self)


@dataclass(frozen=True)
class CalibrationProposal:
    proposal_id: str
    audit_id: str
    config_key: str
    current_value: Any
    proposed_value: Any
    fixture_refs: tuple[EvidenceRef, ...]
    status: str = "BORRADOR"
    test_result: str = "NO_EJECUTADO"
    version: int = 1
    approval: LaboratoryApproval | None = None
    limitations: tuple[str, ...] = ()

    def __post_init__(self):
        _identifier(self.proposal_id, "proposal_id")
        _identifier(self.audit_id, "audit_id")
        if not isinstance(self.config_key, str) or not self.config_key.strip():
            raise ValueError("config_key obligatorio")
        if self.status not in AUDIT_STATES or type(self.version) is not int or self.version < 1:
            raise ValueError("Estado o versión de propuesta inválidos")
        if self.status in ("APROBADA", "APLICADA_LOCALMENTE") and self.approval is None:
            raise ValueError("Aprobación identificada de laboratorio requerida")
        if self.status == "APLICADA_LOCALMENTE" and self.test_result != "PASS":
            raise ValueError("Aplicación local requiere prueba aprobada")
        to_json_dict(self)


@dataclass(frozen=True)
class AssistantLimits:
    max_context_chars: int = 12_000
    max_output_chars: int = 4_000
    max_tool_calls: int = 8
    timeout_seconds: int = 20

    def __post_init__(self):
        values = (self.max_context_chars, self.max_output_chars, self.max_tool_calls, self.timeout_seconds)
        if any(type(value) is not int or value < 1 for value in values):
            raise ValueError("Los límites del asistente deben ser enteros positivos")


@dataclass(frozen=True)
class ToolResult:
    tool_name: str
    data: dict[str, Any]
    evidence: tuple[EvidenceRef, ...]

    def __post_init__(self):
        _identifier(self.tool_name, "tool_name")
        to_json_dict(self)


class AssistantTool(Protocol):
    name: str
    read_only: Literal[True]
    input_schema: dict[str, Any]

    def execute(self, arguments: dict[str, Any]) -> ToolResult: ...


@dataclass(frozen=True)
class AssistantResponse:
    text: str
    evidence: tuple[EvidenceRef, ...]
    tool_trace: tuple[str, ...] = ()
    status: Literal["DRAFT", "FALLBACK", "ERROR"] = "DRAFT"

    def __post_init__(self):
        if self.status not in ("DRAFT", "FALLBACK", "ERROR"):
            raise ValueError("Estado de respuesta inválido")
        to_json_dict(self)


class AIProvider(Protocol):
    provider_id: str
    is_external: bool

    def generate(self, question: str, evidence: tuple[EvidenceRef, ...],
                 limits: AssistantLimits) -> AssistantResponse: ...


@dataclass(frozen=True)
class InvestigationDraft:
    draft_id: str
    alert_ids: tuple[str, ...]
    event_ids: tuple[str, ...]
    interpretation: str
    checks_proposed: tuple[str, ...]
    evidence: tuple[EvidenceRef, ...]
    missing_information: tuple[str, ...]
    provider_id: str
    status: Literal["DRAFT"] = "DRAFT"

    def __post_init__(self):
        _identifier(self.draft_id, "draft_id")
        _identifier(self.provider_id, "provider_id")
        if self.status != "DRAFT" or not self.alert_ids or not self.event_ids:
            raise ValueError("Solo se admiten borradores vinculados a alertas y eventos")
        for identifier in (*self.alert_ids, *self.event_ids):
            _identifier(identifier, "alert_or_event_id")
        if not self.interpretation.strip():
            raise ValueError("Interpretación obligatoria")
        to_json_dict(self)
