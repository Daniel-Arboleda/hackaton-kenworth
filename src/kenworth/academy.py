"""Local learning library for the synthetic Kenworth laboratory."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Concept:
    term: str
    definition: str
    laboratory_example: str
    caution: str


_CONCEPTS = (
    Concept("Evento", "Registro de una actividad observada por una fuente.", "E0321 es un evento del CSV sintético.", "Un evento no demuestra una amenaza."),
    Concept("Alerta", "Señal producida por una regla de detección para revisión.", "AL001 señala acceso fuera del horario de prueba.", "Una alerta no confirma un incidente."),
    Concept("Incidente", "Situación evaluada y confirmada mediante un proceso humano y evidencia suficiente.", "El MVP no confirma incidentes automáticamente.", "No use el conteo de alertas como conteo de incidentes."),
    Concept("Amenaza", "Causa potencial de un daño, que requiere contexto para evaluarse.", "Los fallos de AL006 admiten varias causas posibles.", "No atribuya intención solo por una señal."),
    Concept("Riesgo", "Relación entre impacto y exposición usada aquí para ordenar una revisión.", "DB-LAB recibe prioridad didáctica 9/9.", "La puntuación no es probabilidad de ataque ni severidad de incidente."),
    Concept("Vulnerabilidad", "Debilidad verificable en un sistema o proceso.", "H02 describe una condición administrativa de prueba.", "Un hallazgo inicial no certifica una vulnerabilidad explotable."),
    Concept("Exposición", "Relaciones y condiciones observadas que justifican revisión preventiva.", "R02 y eventos allow se relacionan con DB-LAB.", "Allow no prueba conectividad completa o compromiso."),
    Concept("Criticidad", "Importancia supuesta de un activo en el inventario del laboratorio.", "DB-LAB figura con criticidad Alta.", "La criticidad real requiere validación del propietario."),
    Concept("Hardening", "Mejora preventiva propuesta para reducir una condición revisada.", "H01 propone acotar R02 y habilitar registro.", "La propuesta no está aprobada ni aplicada."),
    Concept("Correlación", "Relación de señales con evento, activo, regla y contexto.", "AL004 y AL005 comparten E0324.", "Dos señales de un evento no son dos incidentes."),
    Concept("Syslog", "Protocolo de transporte de registros hacia un receptor.", "La fase 2 usa un receptor TCP de laboratorio en loopback.", "No implica conexión con un firewall real."),
    Concept("Palo Alto", "Familia de dispositivos y formatos de registro del fabricante.", "Los parsers se prueban con fixtures sintéticos.", "Un fixture no certifica compatibilidad universal."),
    Concept("Regla de firewall", "Condición documentada para permitir o denegar tráfico.", "R03 contempla TCP/22 y TCP/3389 en la política de prueba.", "La descripción no confirma la configuración efectiva."),
    Concept("Zona", "Segmento lógico usado para describir activos y flujos.", "DB-LAB está en la zona Servidores.", "Un cruce de zona no demuestra movimiento lateral."),
    Concept("Ruta hipotética", "Secuencia candidata de relaciones internas observadas allow.", "Una ruta puede unir activos de distintas zonas.", "No demuestra alcance extremo a extremo ni explotación."),
    Concept("SOC L1/L2/L3", "Roles operativos que algunas organizaciones usan para escalamiento y especialización.", "Un analista puede proponer revisión por otro rol.", "No es una clasificación universal de alertas ni una asignación real de Kenworth."),
    Concept("Aprobación humana", "Decisión identificada y revisable antes de actuar.", "La disposición de AL001 requiere justificación humana.", "Un rol propuesto no equivale a una notificación o aprobación enviada."),
    Concept("Limitaciones de IA", "Restricciones de una asistencia que propone texto a partir de fuentes verificables.", "El fallback determinista puede explicar AL001.", "La IA no confirma incidentes, aprueba cambios ni ejecuta contención."),
)

CONCEPTS = {concept.term: concept for concept in _CONCEPTS}
SCREEN_HELP = {
    "Centro de operaciones": ("Evento", "Alerta", "Riesgo"),
    "Investigaciones": ("Alerta", "Correlación", "Aprobación humana", "Incidente"),
    "Infraestructura": ("Zona", "Exposición", "Ruta hipotética"),
    "Integraciones": ("Syslog", "Palo Alto", "Regla de firewall"),
    "Auditorías y calibración": ("Hardening", "Criticidad", "Aprobación humana"),
    "Academia y ayuda": tuple(CONCEPTS),
    "Configuración": ("Limitaciones de IA", "Aprobación humana"),
}


def search_concepts(query=""):
    """Return stable matches without external requests or generated definitions."""
    query = query.strip().casefold()
    return [concept for concept in _CONCEPTS if not query or query in concept.term.casefold() or query in concept.definition.casefold()]


def help_for(screen):
    return [CONCEPTS[term] for term in SCREEN_HELP.get(screen, ())]


def guided_tutorial():
    """Reference-only walkthrough; no decisions are saved by this function."""
    return (
        ("AL001", "Abra AL001 y lea el evento E0321 y la regla R03.", "La señal no confirma incidente."),
        ("CH01", "Compare origen, usuario, destino y ventana de CH01.", "El cambio es contexto; no cierra automáticamente AL001."),
        ("DB-LAB", "Consulte H01, criticidad y la política R02.", "La prioridad 9/9 es una cola didáctica de revisión."),
        ("Rutas", "Revise los IDs de cada tramo allow observado.", "Una ruta candidata no demuestra movimiento lateral."),
    )
