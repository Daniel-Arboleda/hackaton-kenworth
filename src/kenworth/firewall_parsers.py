"""Conservative commercial-format parsers over synthetic fixtures only.

No device connection is made. The phase 1/2 parser path remains unchanged.
"""

import csv
import hashlib
import io
import re
import shlex
from datetime import datetime, timezone

from kenworth.contracts_v2 import SourceMessage
from kenworth.contracts_v4 import FirewallEvent, FirewallParseResult, SourceDescriptor


_RFC5424 = re.compile(r"^<(\d{1,3})>1 (\S+) (\S+) (\S+) (\S+) (\S+) - (.*)$", re.DOTALL)
_RFC3164 = re.compile(r"^<(\d{1,3})>([A-Z][a-z]{2} +\d{1,2} \d\d:\d\d:\d\d) (\S+) (.*)$", re.DOTALL)
_PAN_COMMON = (
    "future_use_0", "receive_time", "serial_number", "type", "subtype", "future_use_5",
    "generated_time", "source_address", "destination_address", "nat_source_ip",
    "nat_destination_ip", "rule_name", "source_user", "destination_user", "application",
    "virtual_system", "source_zone", "destination_zone", "inbound_interface",
    "outbound_interface", "log_action", "future_use_21", "session_id", "repeat_count",
    "source_port", "destination_port", "nat_source_port", "nat_destination_port",
    "flags", "protocol", "action",
)
_PAN_TRAFFIC = _PAN_COMMON + ("bytes", "bytes_sent", "bytes_received")
_PAN_THREAT = _PAN_COMMON + ("url_or_filename", "threat_id", "category", "severity")
_FORMATS = {"pan_traffic": "palo_alto", "pan_threat": "palo_alto",
            "fortios_traffic": "fortinet", "sfos_firewall": "sophos"}
_VERSIONS = {"palo_alto": ("12.2", "standard-prefix"),
             "fortinet": ("7.4.2",), "sophos": ("21.5",)}
_PAN_ACTIONS = {"allow": "allow", "deny": "deny", "drop": "drop", "drop icmp": "drop",
                "reset both": "reset", "reset client": "reset", "reset server": "reset",
                "reset-both": "reset", "reset-client": "reset", "reset-server": "reset"}
_FORTI_ACTIONS = {"accept": "allow", "deny": "deny", "drop": "drop", "close": "close"}
_SOPHOS_ACTIONS = {"allow": "allow", "allowed": "allow", "deny": "deny",
                   "denied": "deny", "drop": "drop"}


def _unwrap(raw):
    if not raw.startswith("<"):
        return raw, None, None
    match = _RFC5424.fullmatch(raw)
    if match and int(match[1]) <= 191:
        return match[7], match[2], "rfc5424"
    match = _RFC3164.fullmatch(raw)
    if match and int(match[1]) <= 191:
        return match[4], match[2], "rfc3164-no-year"
    raise ValueError("Encabezado Syslog inválido o no compatible")


def _csv(raw):
    try:
        rows = list(csv.reader(io.StringIO(raw, newline=""), strict=True))
    except csv.Error as error:
        raise ValueError("CSV malformado") from error
    if len(rows) != 1:
        raise ValueError("Se requiere un registro CSV por mensaje")
    return rows[0]


def _pairs(raw):
    try:
        tokens = shlex.split(raw, posix=True)
    except ValueError as error:
        raise ValueError("Pares clave=valor malformados") from error
    if not tokens or len(tokens) > 200:
        raise ValueError("Cantidad de campos inválida")
    fields = {}
    for token in tokens:
        if "=" not in token:
            raise ValueError("Token sin clave=valor")
        key, value = token.split("=", 1)
        if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", key) or key in fields:
            raise ValueError("Clave inválida o duplicada")
        fields[key] = value
    return fields


def _integer(value, label, *, maximum=None):
    if value in (None, ""):
        return None
    if not re.fullmatch(r"\d+", value):
        raise ValueError(f"{label} inválido")
    number = int(value)
    if maximum is not None and number > maximum:
        raise ValueError(f"{label} fuera de rango")
    return number


def _timestamp(value):
    if not value:
        return None, None
    for pattern in ("%Y/%m/%d %H:%M:%S", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(value, pattern).isoformat(), None
        except ValueError:
            pass
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise ValueError("Marca temporal de evento inválida") from error
    zone = parsed.strftime("%z") if parsed.tzinfo else None
    return parsed.isoformat(), zone or None


def _event(message, source, format_id, parser_version, fields, known, **values):
    digest = hashlib.sha256((source.source_id + "\0" + message.message_id + "\0" + message.raw).encode()).hexdigest()
    event_time, zone = _timestamp(values.pop("event_time", None))
    explicit_zone = values.pop("timezone", None)
    uncertainty = list(values.pop("uncertainty", ()))
    if event_time and not zone:
        uncertainty.append("Zona horaria del evento no acreditada")
    if source.declared_version is None:
        uncertainty.append("Versión de fabricante no declarada")
    return FirewallEvent(
        event_id="fw-" + digest[:32], source_id=source.source_id, vendor=source.vendor,
        format_id=format_id, parser_version=parser_version, received_at=message.received_at,
        normalized_at=datetime.now(timezone.utc).isoformat(), raw_reference="sha256:" + hashlib.sha256(message.raw.encode()).hexdigest(),
        device_id=values.pop("device_id", source.device_id), declared_version=source.declared_version,
        event_time=event_time, timezone=zone or explicit_zone,
        original_fields=fields, unmapped_fields={key: value for key, value in fields.items() if key not in known},
        uncertainty=tuple(uncertainty), **values)


def _pan(message, source, raw, format_id):
    row = _csv(raw)
    expected = "TRAFFIC" if format_id == "pan_traffic" else "THREAT"
    if len(row) < 32 or row[3] != expected or not row[2]:
        raise ValueError("Firma PAN-OS o prefijo estándar incompleto")
    names = _PAN_TRAFFIC if format_id == "pan_traffic" else _PAN_THREAT
    fields = {name: row[index] for index, name in enumerate(names[:len(row)])}
    fields.update({f"extra_{index}": value for index, value in enumerate(row[len(names):], start=len(names))})
    action_raw = fields.get("action") or None
    action = _PAN_ACTIONS.get((action_raw or "").lower(), "other" if action_raw else "unknown")
    values = dict(device_id=fields.get("serial_number") or source.device_id,
                  event_time=fields.get("generated_time"), action_original=action_raw, action=action,
                  source_ip=fields.get("source_address") or None,
                  destination_ip=fields.get("destination_address") or None,
                  source_port=_integer(fields.get("source_port"), "source_port", maximum=65535),
                  destination_port=_integer(fields.get("destination_port"), "destination_port", maximum=65535),
                  policy_id=fields.get("rule_name") or None, source_zone=fields.get("source_zone") or None,
                  destination_zone=fields.get("destination_zone") or None,
                  inbound_interface=fields.get("inbound_interface") or None,
                  outbound_interface=fields.get("outbound_interface") or None,
                  session_id=fields.get("session_id") or None, application=fields.get("application") or None)
    if format_id == "pan_traffic":
        values.update(bytes_total=_integer(fields.get("bytes"), "bytes"),
                      bytes_sent=_integer(fields.get("bytes_sent"), "bytes_sent"),
                      bytes_received=_integer(fields.get("bytes_received"), "bytes_received"))
    else:
        values.update(threat_id=fields.get("threat_id") or None,
                      threat_name=fields.get("url_or_filename") or None,
                      threat_severity=fields.get("severity") or None)
    return _event(message, source, format_id, "1", fields, set(values) | {
        "serial_number", "generated_time", "action", "source_address", "destination_address", "source_port",
        "destination_port", "rule_name", "source_zone", "destination_zone", "inbound_interface",
        "outbound_interface", "session_id", "application", "bytes", "bytes_sent", "bytes_received",
        "threat_id", "url_or_filename", "severity"}, **values)


def _forti(message, source, raw):
    fields = _pairs(raw)
    if fields.get("type") != "traffic" or fields.get("subtype") != "forward":
        raise ValueError("Solo FortiOS Traffic/forward documentado")
    action_raw = fields.get("action") or None
    stamp = (fields.get("date", "") + " " + fields.get("time", "")).strip() or None
    if stamp and fields.get("tz") and re.fullmatch(r"[+-]\d{4}", fields["tz"]):
        stamp += fields["tz"]
    return _event(message, source, "fortios_traffic", "1", fields,
                  {"type", "subtype", "date", "time", "tz", "devid", "devname", "action", "srcip",
                   "dstip", "srcport", "dstport", "policyid", "srcintf", "dstintf", "sessionid",
                   "app", "sentbyte", "rcvdbyte"},
                  device_id=fields.get("devid") or source.device_id, event_time=stamp,
                  action_original=action_raw,
                  action=_FORTI_ACTIONS.get((action_raw or "").lower(), "other" if action_raw else "unknown"),
                  source_ip=fields.get("srcip") or None, destination_ip=fields.get("dstip") or None,
                  source_port=_integer(fields.get("srcport"), "srcport", maximum=65535),
                  destination_port=_integer(fields.get("dstport"), "dstport", maximum=65535),
                  policy_id=fields.get("policyid") or None,
                  inbound_interface=fields.get("srcintf") or None,
                  outbound_interface=fields.get("dstintf") or None,
                  session_id=fields.get("sessionid") or None, application=fields.get("app") or None,
                  bytes_sent=_integer(fields.get("sentbyte"), "sentbyte"),
                  bytes_received=_integer(fields.get("rcvdbyte"), "rcvdbyte"))


def _sophos(message, source, raw):
    fields = _pairs(raw)
    if fields.get("log_type") != "Firewall" or fields.get("log_component") != "Firewall Rule":
        raise ValueError("Solo SFOS Firewall Rule documentado")
    status = fields.get("status", "").lower()
    subtype = fields.get("log_subtype", "").lower()
    if status and subtype and status in _SOPHOS_ACTIONS and subtype in _SOPHOS_ACTIONS:
        if _SOPHOS_ACTIONS[status] != _SOPHOS_ACTIONS[subtype]:
            raise ValueError("Acción Sophos contradictoria")
    action_raw = fields.get("status") or fields.get("log_subtype") or None
    stamp = fields.get("timestamp") or ((fields.get("date", "") + " " + fields.get("time", "")).strip() or None)
    return _event(message, source, "sfos_firewall", "1", fields,
                  {"log_type", "log_component", "log_subtype", "status", "timestamp", "date", "time",
                   "timezone", "device_serial_id", "device_id", "action", "src_ip", "dst_ip",
                   "src_port", "dst_port", "fw_rule_id", "fw_rule_name", "src_zone", "dst_zone",
                   "in_interface", "out_interface", "con_id", "application", "sent_bytes", "recv_bytes"},
                  device_id=fields.get("device_serial_id") or fields.get("device_id") or source.device_id,
                  event_time=stamp, timezone=fields.get("timezone") or None,
                  action_original=action_raw,
                  action=_SOPHOS_ACTIONS.get((action_raw or "").lower(), "other" if action_raw else "unknown"),
                  source_ip=fields.get("src_ip") or None, destination_ip=fields.get("dst_ip") or None,
                  source_port=_integer(fields.get("src_port"), "src_port", maximum=65535),
                  destination_port=_integer(fields.get("dst_port"), "dst_port", maximum=65535),
                  policy_id=fields.get("fw_rule_id") or fields.get("fw_rule_name") or None,
                  source_zone=fields.get("src_zone") or None, destination_zone=fields.get("dst_zone") or None,
                  inbound_interface=fields.get("in_interface") or None,
                  outbound_interface=fields.get("out_interface") or None,
                  session_id=fields.get("con_id") or None, application=fields.get("application") or None,
                  bytes_sent=_integer(fields.get("sent_bytes"), "sent_bytes"),
                  bytes_received=_integer(fields.get("recv_bytes"), "recv_bytes"))


def _signatures(raw):
    matches = []
    try:
        row = _csv(raw)
        if len(row) >= 32 and row[2] and row[3] in ("TRAFFIC", "THREAT"):
            matches.append("pan_traffic" if row[3] == "TRAFFIC" else "pan_threat")
    except ValueError:
        pass
    try:
        fields = _pairs(raw)
        if fields.get("type") == "traffic" and fields.get("subtype") == "forward" and "logid" in fields:
            matches.append("fortios_traffic")
        if fields.get("log_type") == "Firewall" and fields.get("log_component") == "Firewall Rule" and "log_id" in fields:
            matches.append("sfos_firewall")
    except ValueError:
        pass
    return matches


def parse_firewall_message(message: SourceMessage, source: SourceDescriptor | None = None) -> FirewallParseResult:
    """Prefer configured source, then verified signature; never guess vendor by text."""
    if source is not None and source.source_id != message.source_id:
        return FirewallParseResult("REJECTED", "source_mismatch", message.message_id,
                                   errors=("source_id no coincide con fuente configurada",))
    try:
        payload, _, _ = _unwrap(message.raw)
        signatures = _signatures(payload)
        if source is None:
            if len(signatures) != 1:
                return FirewallParseResult("UNMAPPED", "unknown_format", message.message_id,
                                           errors=("Firma ambigua o desconocida",))
            format_id = signatures[0]
            source = SourceDescriptor(message.source_id, _FORMATS[format_id], format_id)
        else:
            format_id = source.format_id
            if format_id not in _FORMATS or source.vendor != _FORMATS[format_id]:
                return FirewallParseResult("UNMAPPED", "unknown_format", message.message_id,
                                           errors=("Plantilla o fabricante no compatible",))
            # A configured parser can distinguish malformed framing from a
            # well-formed message belonging to another format.
            if format_id.startswith("pan_"):
                configured_row = _csv(payload)
                expected_type = "TRAFFIC" if format_id == "pan_traffic" else "THREAT"
                if len(configured_row) > 3 and configured_row[3] == expected_type and len(configured_row) < 32:
                    raise ValueError("Prefijo PAN-OS truncado")
            else:
                _pairs(payload)
            if format_id not in signatures:
                return FirewallParseResult("UNMAPPED", format_id, message.message_id,
                                           errors=("Firma incompatible con fuente configurada",))
        if source.declared_version and source.declared_version not in _VERSIONS[source.vendor]:
            return FirewallParseResult("UNMAPPED", format_id, message.message_id,
                                       errors=("Versión declarada fuera de plantilla probada",))
        parser = {"pan_traffic": _pan, "pan_threat": _pan,
                  "fortios_traffic": _forti, "sfos_firewall": _sophos}[format_id]
        event = parser(message, source, payload, format_id) if format_id.startswith("pan_") else parser(message, source, payload)
        return FirewallParseResult("NORMALIZED", format_id, message.message_id, event=event)
    except (ValueError, IndexError, TypeError) as error:
        return FirewallParseResult("REJECTED", source.format_id if source else "unknown_format",
                                   message.message_id, errors=(str(error),))
