# Frontend proactivo WP-011

La interfaz Streamlit usa únicamente los datos sintéticos de `Kenworth_Recursos_de_Prueba` y los módulos backend integrados. No recalcula detección, correlación, exposición ni prioridades en la presentación.

## Recorrido breve

1. **Resumen:** confirme 324 eventos, seis alertas y diez activos. La cola agrupa AL004 y AL005 bajo E0324.
2. **Prioridades:** abra el evento más alto de la tabla; vea impacto, exposición, evidencia y acción propuesta. La selección de una fila de detalle requiere un paso después de entrar en la sección.
3. **Riesgos por activo:** seleccione DB-LAB. Consulte criticidad, zona, rol responsable propuesto, hallazgos, políticas observadas, relaciones y prioridad calculada por backend.
4. **Alertas:** examine el evento y el playbook contextual; cualquier clasificación y decisión sigue siendo humana y queda en SQLite.
5. **Topología:** use el mapa por zonas y la leyenda textual. La tabla separa `allow` observado, `deny` y flujos documentados sin verificar; el detalle conserva IDs de eventos.
6. **Rutas hipotéticas:** seleccione un candidato y examine cada tramo y condición no verificada. No equivale a conectividad efectiva, explotación o movimiento lateral.
7. **Hardening:** revise H01, H02 y H05 con prioridad de revisión, evidencia, impacto cualitativo, validación y reversión.
8. **Reporte:** descargue Markdown generado en memoria. Incluye fecha, dataset, alertas, investigaciones, activos con hallazgos, exposición, hardening, decisiones guardadas y límites.

## Ejecución y validación

Desde un worktree aislado, asigne un puerto libre y nombre Compose exclusivo:

```powershell
$env:PORT = '18511'
docker compose -p kenworth-wp011 -f .\compose.yaml up --build -d
docker compose -p kenworth-wp011 -f .\compose.yaml ps
```

Abra `http://localhost:18511`. La base SQLite queda en un volumen de ese proyecto y no altera otros entornos. Para pruebas, ejecute `python -m unittest discover -s tests` y `.\scripts\test-p01.ps1`. Los AppTests requieren Streamlit y se ejecutan dentro del contenedor; no cuente omisiones locales como pruebas aprobadas.

El informe descargado registra propuestas; no aplica cambios, no crea tickets y no confirma incidentes. `allow` es una observación, `deny` y los flujos documentados no son transitables. La prioridad 1–9 es un orden didáctico de revisión, sin probabilidad de compromiso ni severidad de incidente.
