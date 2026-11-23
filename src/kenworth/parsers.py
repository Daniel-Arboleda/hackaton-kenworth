"""Conservative adapters for synthetic lab messages.

Each parser accepts an explicitly identified shape. Unknown data stays unmapped.
"""

import csv
import io
import json
import re
from typing import Iterable

from kenworth.contracts_v2 import FormatMatch, NormalizedEvent, ParseResult, SourceMessage
from kenworth.ingestion import FIELDS


_SYSLOG = re.compile(r"^<(\d{1,3})>1 (\S+) (\S+) (\S+) (\S+) (\S+) - (.*)$", re.DOTALL)
_PAIR = re.compile(r"(?:^|\s)([A-Za-z][A-Za-z0-9_]*)=([^\s]+)")
_PAN_FIELDS = (
    "future_use", "receive_time", "serial_number", "type", "subtype", "config_version",
    "generated_time", "source_address", "destination_address", "nat_source_ip",
    "nat_destination_ip", "rule_name", "source_user", "destination_user", "application",
    "virtual_system", "source_zone", "destination_zone", "inbound_interface",
    "outbound_interface", "log_action", "time_logged", "session_id", "repeat_count",
    "source_port", "destination_port", "nat_source_port", "nat_destination_port",
    "flags", "protocol", "action", "bytes",
)


def _result(message, parser_id, fields, mapped, *, vendor, family, timestamp=None):
    original = dict(fields)
    trace = {"vendor": vendor, "log_family": family, "source": message.source_id,
             "parser": parser_id, "parser_version": "1", "received_at": message.received_at,
             "event_timestamp": timestamp, "result": "UNMAPPED"}
    if mapped is None:
        return ParseResult("UNMAPPED", parser_id, message.message_id,
                           errors=("Campos canónicos insuficientes o no compatibles",),
                           raw_fields={"original": original, "provenance": trace})
    missing = [field for field in FIELDS if mapped.get(field) in (None, "")]
    if missing:
        return ParseResult("UNMAPPED", parser_id, message.message_id,
                           errors=("Campos canónicos ausentes: " + ", ".join(missing),),
                           raw_fields={"original": original, "provenance": trace})
    unmapped = {key: value for key, value in original.items() if key not in mapped}
    try:
        event = NormalizedEvent.from_legacy(
            {name: str(mapped[name]) for name in FIELDS}, source_id=message.source_id,
            parser_id=parser_id, parser_version="1", raw_fields=original,
            unmapped_fields=unmapped,
        )
    except (ValueError, KeyError, TypeError) as error:
        return ParseResult("REJECTED", parser_id, message.message_id,
                           errors=(str(error),), raw_fields={"original": original, "provenance": trace})
    trace["result"] = "NORMALIZED"
    return ParseResult("NORMALIZED", parser_id, message.message_id, event=event,
                       raw_fields={"original": original, "provenance": trace})


class CanonicalCSVParser:
    parser_id = "canonical_csv"
    version = "1"

    def identify(self, message):
        first = message.raw.splitlines()[0] if message.raw else ""
        try:
            header = next(csv.reader([first]))
        except csv.Error:
            header = []
        return FormatMatch(self.parser_id, set(FIELDS).issubset(header),
                           ("encabezado con los 12 campos canónicos",) if set(FIELDS).issubset(header) else ())

    def parse(self, message):
        try:
            rows = list(csv.DictReader(io.StringIO(message.raw, newline=""), strict=True))
            if len(rows) != 1 or not set(FIELDS).issubset(rows[0]) or None in rows[0]:
                raise ValueError("Se requiere exactamente una fila CSV canónica")
        except (csv.Error, ValueError) as error:
            return ParseResult("REJECTED", self.parser_id, message.message_id, errors=(str(error),))
        return _result(message, self.parser_id, rows[0],
                       {name: rows[0][name] for name in FIELDS}, vendor="kenworth_lab",
                       family="canonical_csv", timestamp=rows[0].get("fecha_hora"))


class NormalizedJSONParser:
    parser_id = "normalized_json"
    version = "1"

    def identify(self, message):
        try:
            data = json.loads(message.raw)
        except (ValueError, TypeError):
            data = None
        matched = isinstance(data, dict) and data.get("schema") == "kenworth.normalized.v1"
        return FormatMatch(self.parser_id, matched,
                           ("schema=kenworth.normalized.v1",) if matched else ())

    def parse(self, message):
        try:
            data = json.loads(message.raw)
            if not isinstance(data, dict) or data.get("schema") != "kenworth.normalized.v1":
                raise ValueError("Esquema JSON no compatible")
            fields = data.get("event")
            if not isinstance(fields, dict):
                raise ValueError("event debe ser un objeto")
        except (ValueError, TypeError) as error:
            return ParseResult("REJECTED", self.parser_id, message.message_id, errors=(str(error),))
        result = _result(message, self.parser_id, {"schema": data["schema"], **fields},
                         {name: fields[name] for name in FIELDS if name in fields}, vendor="kenworth_lab",
                         family="normalized_json", timestamp=fields.get("fecha_hora"))
        return result


class GenericSyslogParser:
    parser_id = "generic_syslog"
    version = "1"

    def identify(self, message):
        match = _SYSLOG.fullmatch(message.raw)
        matched = bool(match and int(match[1]) <= 191)
        return FormatMatch(self.parser_id, matched,
                           ("PRI 0..191 y encabezado RFC 5424 versión 1",) if matched else ())

    def parse(self, message):
        match = _SYSLOG.fullmatch(message.raw)
        if not match or int(match[1]) > 191:
            return ParseResult("REJECTED", self.parser_id, message.message_id,
                               errors=("Encabezado Syslog no compatible",))
        header = dict(zip(("pri", "timestamp", "host", "app", "procid", "msgid"), match.groups()[:6]))
        fields = dict(_PAIR.findall(match[7]))
        raw = {**header, "message": match[7], **fields}
        return _result(message, self.parser_id, raw,
                       {name: fields[name] for name in FIELDS if name in fields}, vendor="generic",
                       family="syslog", timestamp=header["timestamp"])


class PaloAltoTrafficParser:
    """Narrow PAN-OS Traffic CSV prefix; later columns remain unmapped."""

    parser_id = "panos_traffic"
    version = "1"

    def identify(self, message):
        try:
            row = next(csv.reader([message.raw], strict=True))
        except (csv.Error, StopIteration):
            row = []
        matched = len(row) >= 32 and row[3] == "TRAFFIC" and bool(row[2])
        return FormatMatch(self.parser_id, matched,
                           ("CSV PAN-OS: columna 4 TRAFFIC, serie y 32 columnas iniciales",) if matched else ())

    def parse(self, message):
        try:
            row = next(csv.reader([message.raw], strict=True))
            if len(row) < 32 or row[3] != "TRAFFIC":
                raise ValueError("Prefijo PAN-OS Traffic no compatible")
        except (csv.Error, StopIteration, ValueError) as error:
            return ParseResult("REJECTED", self.parser_id, message.message_id, errors=(str(error),))
        fields = dict(zip(_PAN_FIELDS, row[:32]))
        fields.update({f"extra_{index}": value for index, value in enumerate(row[32:], start=32)})
        # Canonical-only values absent in PAN-OS are deliberately not fabricated.
        lab_extension = dict(_PAIR.findall(" ".join(row[32:])))
        mapped = {"evento_id": fields["session_id"], "fecha_hora": fields["generated_time"],
                  "zona_horaria": lab_extension.get("lab_timezone"), "tipo": "trafico",
                  "origen_ip": fields["source_address"], "destino_ip": fields["destination_address"],
                  "puerto_destino": fields["destination_port"], "accion": fields["action"],
                  "regla_id": fields["rule_name"], "usuario_prueba": fields["source_user"],
                  "resultado": fields["subtype"], "bytes": fields["bytes"]}
        # The canonical timezone and user must be explicit in the lab fixture.
        if not fields["source_user"] or not lab_extension.get("lab_timezone"):
            mapped = None
        return _result(message, self.parser_id, fields, mapped, vendor="Palo Alto Networks",
                       family="Traffic", timestamp=fields["generated_time"])


PARSERS = (CanonicalCSVParser(), NormalizedJSONParser(), PaloAltoTrafficParser(), GenericSyslogParser())


def detect_format(message: SourceMessage, parsers: Iterable = PARSERS) -> tuple[FormatMatch, ...]:
    return tuple(parser.identify(message) for parser in parsers)


def parse_message(message: SourceMessage, parsers: Iterable = PARSERS) -> ParseResult:
    for parser in parsers:
        if parser.identify(message).matched:
            return parser.parse(message)
    return ParseResult("UNMAPPED", "unknown_format", message.message_id,
                       errors=("Ninguna firma de formato admitida coincide",),
                       raw_fields={"original_message": message.raw,
                                   "provenance": {"source": message.source_id,
                                                  "received_at": message.received_at,
                                                  "result": "UNMAPPED"}})


class ReadOnlyAPIConnector:
    """Disabled contract placeholder. No URL, credential, or network methods exist."""

    kind = "api_read_only_stub"

    def __init__(self, source_id="api_stub"):
        self.source_id = source_id

    def health(self):
        from kenworth.contracts_v2 import SourceHealth
        return SourceHealth(self.source_id, "STOPPED", detail="Conector API no configurado")

    def iter_messages(self, limit):
        if not isinstance(limit, int) or limit < 1:
            raise ValueError("limit debe ser positivo")
        return iter(())
