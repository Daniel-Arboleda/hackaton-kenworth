from collections import defaultdict, deque
from datetime import datetime, timedelta


def detect(events, cfg):
    alerts = []
    windows = defaultdict(deque)
    triggered = {}

    def add(event, kind, reason):
        alerts.append({'alerta_id': f'AL{len(alerts)+1:03}', 'evento_id': event['evento_id'], 'fecha_hora': event['fecha_hora'], 'tipo': kind, 'motivo': reason, 'disposicion': 'Revisar contexto; no confirma incidente'})

    for event in sorted(events, key=lambda row: (row['fecha_hora'], row['evento_id'])):
        moment = datetime.fromisoformat(event['fecha_hora'])
        key = (event['origen_ip'], event['destino_ip'], event['usuario_prueba'])
        if event['tipo'] == 'autenticacion' and event['resultado'] == 'fallo':
            window = windows[key]
            window.append(moment)
            while window and moment - window[0] > timedelta(minutes=cfg['ventana_minutos']):
                window.popleft()
            if len(window) >= cfg['fallos_umbral'] and (key not in triggered or moment - triggered[key] > timedelta(minutes=cfg['ventana_minutos'])):
                add(event, 'Fallos repetidos', f'{len(window)} fallos en ventana móvil; origen, destino y usuario coincidentes')
                triggered[key] = moment
        if event['tipo'] == 'autenticacion' and event['resultado'] == 'exito' and not cfg['hora_inicio'] <= moment.hour < cfg['hora_fin']:
            add(event, 'Fuera de horario', 'Acceso exitoso fuera de horario de prueba; revisar cambios autorizados')
        if int(event['bytes']) >= cfg['volumen_revision_bytes']:
            add(event, 'Volumen para revisión', 'Volumen supera el umbral de prueba; no confirma extracción de información')
        if event['regla_id'] == 'R01' and not (event['destino_ip'] == '10.60.10.10' and int(event['puerto_destino']) == 443 and event['accion'] == 'allow'):
            add(event, 'Inconsistencia de registro', 'Destino, servicio o acción no coinciden con la descripción simplificada de R01')
    return alerts
