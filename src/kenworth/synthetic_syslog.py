"""Stoppable synthetic Syslog sender; loopback only and no original data edits."""

import argparse
import socket
import threading
from datetime import datetime, timedelta, timezone


def sample_message(index):
    if type(index) is not int or not 0 <= index <= 999999:
        raise ValueError("Índice sintético fuera de rango")
    timestamp = datetime.now(timezone.utc).isoformat()
    return f"<134>1 {timestamp} LAB-SYNTHETIC generator - - - event_id=SYN-{index:06d} action=allow".encode("utf-8") + b"\n"


def canonical_sample_message(index):
    """A complete synthetic canonical event for the parser and detection demo."""
    if type(index) is not int or not 0 <= index <= 999999:
        raise ValueError("Índice sintético fuera de rango")
    timestamp = datetime.now(timezone(timedelta(hours=-5))).isoformat()
    fields = (f"evento_id=SYN-{index:06d}", f"fecha_hora={timestamp}",
              "zona_horaria=America/Bogota", "tipo=trafico", "origen_ip=192.0.2.10",
              "destino_ip=198.51.100.20", "puerto_destino=443", "accion=allow",
              "regla_id=LAB-RULE", "usuario_prueba=usuario-lab", "resultado=permitido",
              "bytes=999999999")
    return f"<134>1 {timestamp} LAB-SYNTHETIC generator - LAB - {' '.join(fields)}".encode("utf-8") + b"\n"


def send_samples(port, *, count=10, interval=0.1, stop_event=None, retries=3, canonical=False):
    """Send bounded samples; retry only loopback and stop promptly when asked."""
    if type(port) is not int or not 1 <= port <= 65535:
        raise ValueError("Puerto inválido")
    if type(count) is not int or not 0 <= count <= 10000:
        raise ValueError("Cantidad fuera de rango")
    if not isinstance(interval, (int, float)) or not 0 <= interval <= 10:
        raise ValueError("Intervalo fuera de rango")
    if type(retries) is not int or not 1 <= retries <= 5:
        raise ValueError("Reintentos fuera de rango")
    stop_event = stop_event or threading.Event()
    sent = 0
    for index in range(count):
        if stop_event.is_set():
            break
        payload = canonical_sample_message(index) if canonical else sample_message(index)
        for attempt in range(retries):
            if stop_event.is_set():
                return sent
            try:
                with socket.create_connection(("127.0.0.1", port), timeout=2) as connection:
                    connection.sendall(payload)
                sent += 1
                break
            except OSError:
                if attempt + 1 == retries:
                    raise
                if stop_event.wait(min(0.1 * (2 ** attempt), 0.5)):
                    return sent
        if stop_event.wait(interval):
            break
    return sent


def main(argv=None):
    parser = argparse.ArgumentParser(description="Generador Syslog sintético local")
    parser.add_argument("--port", type=int, default=18519)
    parser.add_argument("--count", type=int, default=10)
    parser.add_argument("--interval", type=float, default=0.1)
    parser.add_argument("--canonical", action="store_true", help="Enviar eventos canónicos sintéticos")
    args = parser.parse_args(argv)
    stop = threading.Event()
    try:
        sent = send_samples(args.port, count=args.count, interval=args.interval,
                            stop_event=stop, canonical=args.canonical)
    except KeyboardInterrupt:
        stop.set()
        sent = 0
    print(f"Mensajes sintéticos enviados: {sent}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
