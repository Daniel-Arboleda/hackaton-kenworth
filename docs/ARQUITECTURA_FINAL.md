# Arquitectura y contratos del MVP

## Extensión de fase 2

WP-014 fijó `contracts_v2.py` y esquemas sin romper las APIs de fase 1. El archivo CSV original sigue alimentando el tablero estable. En paralelo, `syslog_receiver.py` acepta TCP solo en `127.0.0.1` como proceso independiente; `parsers.py` identifica CSV canónico, JSON con esquema, Syslog genérico y un prefijo Palo Alto Traffic sintético. `phase2_flows.py` pasa únicamente eventos normalizados al detector existente y devuelve alertas provisionales sin persistir decisiones. No hay conexión a un firewall real.

`topology_graph.py` presenta el grafo calculado por `topology.py`/`exposure.py` con procedencia y filtros. `audit.py` produce ocho evaluaciones de lectura; `calibration.py` valida y versiona ajustes solo en JSON derivado local. `academy.py` y `academy_ui.py` ofrecen glosario, tutoriales y ayuda contextual. `drafts.py` conserva borradores por token en SQLite separado, con expiración; únicamente `storage.py` guarda decisiones definitivas.

`assistant.py` usa herramientas de solo lectura de `assistant_tools.py` y adaptadores de `assistant_providers.py`. El fallback determinista funciona sin red. Los adaptadores externos están deshabilitados por defecto y se probaron con transportes falsos; no se afirma compatibilidad de API en producción. La UI de `app.py` monta estos componentes, mantiene el receptor separado y muestra límites explícitos. Consulte [contratos de fase 2](CONTRATOS_FASE2_WP014.md), [integración funcional](INTEGRACION_FUNCIONAL_WP022.md) y [QA](QA_FASE2_WP023.md).

## Extensión SENTRIX de Fase 3

El contenedor web conserva el motor determinista y un volumen SQLite de laboratorio. El perfil Compose opcional `collector` ejecuta el receptor Syslog loopback y `continuous_pipeline.py` en un segundo contenedor con el mismo volumen, sin publicar su puerto. El pipeline guarda cursor, estado de parseo, eventos canónicos y alertas provisionales; `app.py` lee una instantánea de esos conteos en Panorama. La cola en memoria regula la entrada y puede rechazar mensajes cuando se llena. El detalle de investigación del dashboard continúa basado en el archivo sintético hasta una integración posterior.

`operations.py` agrega prioridades y decisiones humanas locales en una vista de solo lectura. `investigation_journey.py` conecta alertas con relaciones y hallazgos existentes, sin inferir aristas. `assistant_runtime.py` habilita un modelo HTTP loopback solo mediante configuración explícita; `AssistantService` conserva el fallback y las herramientas de lectura. Consulte [modelo de amenazas](MODELO_AMENAZAS_WP025.md) y [QA de Fase 3](QA_ENTREGA_FASE3_WP030.md). La red bridge del contenedor no bloquea egress por sí misma.

## Flujo y módulos

```text
CSV y configuraciones sintéticas
  → ingestion.py (validación y contexto)
  → detection.py (cuatro señales)
  → correlation.py + explanations.py + playbooks.py (contexto y propuesta)
  → topology.py (relaciones etiquetadas)
  → exposure.py (rutas candidatas y límites)
  → prioritization.py (cola preventiva 1–9)
  → app.py (Streamlit) → storage.py (decisión humana SQLite)
                       → reports.py (Markdown descargable en memoria)
```

| Módulo | Responsabilidad | Salida principal |
|---|---|---|
| `ingestion.py` | Validar CSV y cargar inventario, políticas, cambios, hallazgos y umbrales | 324 eventos únicos y contexto |
| `detection.py` | Reglas didácticas sin efectos secundarios | Seis diccionarios de alerta con seis campos de referencia |
| `correlation.py` | Relacionar evento, IP inventariada, política y cambios | Evidencia contextual; CH01 no cierra alertas |
| `explanations.py` | Interpretación prudente y faltantes | Explicación trazable por alerta |
| `playbooks.py` | Verificaciones y acciones humanas propuestas | Cuatro playbooks deterministas |
| `topology.py` | Activos, nodos externos y relaciones etiquetadas | 103 relaciones observadas y tres flujos documentados |
| `exposure.py` | Rutas internas candidatas y hallazgos administrativos | Tramos con IDs de evidencia; hipótesis vertical no evaluable |
| `prioritization.py` | Matriz didáctica y agrupación por evento | Investigaciones, tres propuestas, prioridad por diez activos, escenario R02 |
| `storage.py` | Validar y conservar decisiones humanas | SQLite por `alerta_id` |
| `reports.py` | Resumen reproducible de una ejecución | Markdown, sin escritura en servidor |
| `app.py` | Navegación y presentación | Dashboard Streamlit local |

La aplicación es un monolito modular Python. `compose.yaml` monta los recursos sintéticos como solo lectura, mantiene SQLite en volumen separado y publica Streamlit solo en `127.0.0.1`. El contenedor utiliza usuario no privilegiado y `no-new-privileges`. No hay API adicional, SIEM ni SOAR.

## Modelo de datos y procedencia

- `02_Datos/eventos_normalizados.csv` es la fuente de eventos; JSONL contiene la misma colección, pero no se usa en el MVP. `evento_id` es único y la fecha ISO representa `America/Bogota`.
- `02_Datos/inventario_activos.csv` contiene diez activos de prueba con IP, zona, criticidad y rol responsable propuesto.
- `03_Configuraciones/politicas_firewall_prueba.csv` describe R01–R04; la descripción no prueba configuración efectiva.
- `02_Datos/cambios_autorizados.csv` aporta contexto. CH01 cubre una ventana y origen específicos de BACKUP-LAB; no autoriza toda actividad posterior.
- `02_Datos/hallazgos_iniciales.csv` registra H01–H07. Los hallazgos son hipótesis del laboratorio, no CVE.
- `01_Contexto/Topologia_de_prueba.txt` sustenta tres flujos deseados explícitos que permanecen sin verificar.
- `07_Validacion/` contiene referencias y casos controlados. Los scripts de aceptación comparan contra ellas sin editarlas.
- SQLite tiene una tabla `decisions` con `alerta_id` como clave, `estado`, `justificacion`, `actualizado`, `disposicion`, `rol_destinatario` y `responsable`. No guarda eventos ni crea incidentes. `save` exige justificación y disposición compatible con un cierre.

## Reglas y correlación

Los umbrales vienen de `03_Configuraciones/parametros_alertas.json`:

1. Cinco fallos de autenticación con mismo origen, destino y usuario en ventana móvil de diez minutos.
2. Acceso exitoso fuera de 07:00–19:00, horario didáctico.
3. Volumen de al menos 50 000 000 bytes: revisión, sin inferir extracción.
4. Registro R01 cuyo destino, puerto o acción difiere de su descripción simplificada.

AL001, E0321 y CH01 ilustran que un cambio puede coincidir sin justificar automáticamente toda actividad. AL006, E0305 reúne cinco fallos, sin demostrar acceso posterior. AL004 y AL005 son dos señales del mismo E0324; la cola las agrupa por evento para evitar duplicar una investigación como si fueran incidentes.

## Exposición, prioridad y hardening

`topology.py` conserva `source`, `target`, puerto, acción, fuente, IDs de eventos y verificación. `exposure.py` solo recorre aristas internas observadas `allow` con IDs; excluye `deny`, flujos documentados y nodos externos, limita saltos y evita ciclos. Un tramo observado no prueba conectividad extremo a extremo. Los hallazgos administrativos H02 y H07 retornan `NO_EVALUABLE_CON_EVIDENCIA_ACTUAL` para privilegios por falta de identidades, permisos y mecanismos.

`prioritization.py` asigna impacto 1–3 según criticidad y exposición 1–3 según evidencia `allow`, rutas candidatas o H01/R02; el producto posible es 1, 2, 3, 4, 6 o 9. 1–2 es baja, 3–4 media y 6–9 alta. Esta cifra ordena revisión, no es severidad ni probabilidad. Conserva las tres propuestas H01, H02 y H05 con justificación, acción, responsable propuesto, validación y reversión. El escenario contrafactual R02 describe una posible reducción cualitativa de flujos futuros si un cambio fuera aprobado; no modifica la regla ni borra eventos.

Contratos detallados: [ingesta y SQLite](contracts.md), [topología](topology_contract.md), [exposición](exposure_contract.md), [priorización](prioritization_contract.md), [explicaciones y playbooks](EXPLICACIONES_PLAYBOOKS_WP006.md).
