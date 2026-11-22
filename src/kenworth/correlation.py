from datetime import datetime


def investigate(alert, events, context):
    event = next(row for row in events if row['evento_id'] == alert['evento_id'])
    by_ip = {row['ip_prueba']: row for row in context['assets']}
    destination = by_ip.get(event['destino_ip'])
    source = by_ip.get(event['origen_ip'])
    policy = next((row for row in context['policies'] if row['regla_id'] == event['regla_id']), None)
    moment = datetime.fromisoformat(event['fecha_hora'])
    changes = [row for row in context['changes'] if destination and row['activo'] == destination['nombre_prueba'] and row['origen_autorizado'] == event['origen_ip'] and row['usuario_prueba'] == event['usuario_prueba'] and datetime.fromisoformat(row['inicio']) <= moment <= datetime.fromisoformat(row['fin'])]
    return {'event': event, 'source': source, 'destination': destination, 'policy': policy, 'matching_changes': changes, 'note': 'El cambio es contexto; la disposición requiere revisión humana.'}
