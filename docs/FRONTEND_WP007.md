# Frontend de contingencia WP-007

Esta rama presenta el laboratorio sintético de Kenworth en Streamlit. No integra el frontend de Alejandra ni confirma incidentes reales.

## Arranque

Desde este worktree, con Docker Desktop disponible:

```powershell
$env:PORT = '18507'
docker compose -p kenworth-wp007 -f .\compose.yaml up --build -d
docker compose -p kenworth-wp007 -f .\compose.yaml ps
```

Abra `http://localhost:18507`. El proyecto Compose y el volumen SQLite tienen nombres propios. No use `down -v` si desea conservar decisiones.

## Navegación y demostración

1. **Resumen:** compruebe 324 eventos, 6 alertas y 10 activos; observe categorías y estado de revisión calculado desde SQLite.
2. **Alertas:** filtre, abra AL001, vea el evento original, la política R03 y el cambio CH01. CH01 no cierra la señal automáticamente.
3. **Decisión humana:** registre estado, disposición, rol destinatario y justificación. La decisión queda en SQLite; ningún aviso o bloqueo se ejecuta.
4. **Topología:** consulte DB-LAB; compare comunicaciones observadas, denegadas y flujos documentados no verificados. Los IDs de eventos respaldan cada relación.
5. **Hardening:** muestre tres propuestas con evidencia, validación y reversión.
6. **Validación:** lea los siete casos P01. Los reportes locales aparecen solo si el directorio de evidencia está disponible; Docker no lo monta por defecto. El dashboard no ejecuta P01.
7. **Demo guiada:** repita el flujo de alerta a decisión y recomendación desde una sola vista.

## Pruebas y límites

`python -m unittest discover -s tests -p "test_*.py" -v` ejecuta las pruebas de backend; los tests de interfaz requieren Streamlit y se ejecutan dentro del contenedor. `.\scripts\test-p01.ps1` verifica el CSV y las referencias. El frontend usa `detect`, `investigate`, `plan`, `build_topology` y `analyze_asset` sin reimplementar sus reglas.

Los datos son sintéticos. `allow` no demuestra conectividad completa ni compromiso; `deny` no se trata como ruta transitable. No hay escaneo, IA externa, SOAR real, tickets ni acciones automáticas sobre dispositivos.
