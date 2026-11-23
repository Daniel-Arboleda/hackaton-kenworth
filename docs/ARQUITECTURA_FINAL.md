# Arquitectura y contratos del MVP

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
