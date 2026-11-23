# Kenworth Security Monitor

MVP local de apoyo a decisiones preventivas sobre el **laboratorio sintético Estud-IA**. No representa infraestructura, vulnerabilidades ni incidentes confirmados de Kenworth. Convierte eventos en alertas, contexto, exposición potencial, prioridad de revisión, propuestas de hardening y decisiones humanas registradas.

## Inicio rápido

Requiere Docker Desktop con Compose y un puerto local libre. En PowerShell, desde la raíz del repositorio:

```powershell
$env:PORT = '18513'
docker compose -p kenworth-demo -f .\compose.yaml up --build -d
docker compose -p kenworth-demo -f .\compose.yaml ps
```

Abra `http://localhost:18513`. El servicio se publica únicamente en `127.0.0.1`. Los recursos de prueba se montan en modo solo lectura y las decisiones se guardan en un volumen SQLite exclusivo del proyecto Compose. Para detenerlo sin borrar decisiones:

```powershell
docker compose -p kenworth-demo -f .\compose.yaml down
```

Si Docker informa que agotó sus pools para crear una subred nueva, use el `bridge` existente con el [override local](compose.bridge.yaml): `docker compose -p kenworth-demo -f .\compose.yaml -f .\compose.bridge.yaml up --build -d`. Conserve el mismo proyecto, puerto y volumen; deténgalo con ambos `-f` y `down` **sin `-v`**. Esta alternativa no modifica redes o volúmenes de otros proyectos.

## Qué permite hacer

- Revisar 324 eventos, seis alertas de cuatro reglas y diez activos del laboratorio.
- Investigar alertas con evento original, regla, activo, política, cambio coincidente, explicación y playbook propuesto.
- Registrar una decisión humana justificada en SQLite; asignar un rol propuesto no envía notificaciones.
- Explorar relaciones observadas `allow` y `deny`, flujos documentados no verificados y rutas hipotéticas con evidencia de cada tramo.
- Consultar una cola de prioridad didáctica 1–9 y tres acciones de hardening propuestas.
- Descargar un informe Markdown local generado en memoria, con procedencia y límites.

## Validación

```powershell
python -m unittest discover -s tests
.\scripts\test-p01.ps1
.\scripts\test-p02.ps1
.\scripts\test-p03.ps1
.\scripts\test-all.ps1
.\scripts\test-e2e.ps1
```

Las pruebas Streamlit AppTest requieren Streamlit; si Python local no lo tiene, se omiten allí y se ejecutan en Docker. P01 compara las referencias de 324 eventos y seis alertas; P02 verifica correlación; P03 verifica exposición y priorización. E2E usa proyecto, puerto y volumen aislados. La evidencia de ejecución se guarda en `artifacts/acceptance/`, excluida de Git. Consulte [validación](docs/VALIDACION_WP012.md).

## Documentación

- [Arquitectura, módulos y contratos](docs/ARQUITECTURA_FINAL.md)
- [Instalación y manual de usuario](docs/MANUAL_INSTALACION_USUARIO.md)
- [Informe del reto](docs/INFORME_RETO.md)
- [Guion de demostración de 3–5 minutos](docs/GUION_DEMO.md)
- [Dependencias, licencias y evolución](docs/DEPENDENCIAS_Y_EVOLUCION.md)
- [Plan y estado de los incrementos](docs/PLAN_EJECUCION_WP008_WP013.md)

## Límites

Sin conexión con Kenworth ni Palo Alto real, autenticación, escaneo, explotación, cambios de firewall, bloqueos automáticos, IA generativa, tickets externos o confirmación automática de incidentes. Un `allow` observado no prueba conectividad completa; una ruta candidata no demuestra movimiento lateral. La prioridad ordena revisión, no expresa probabilidad ni severidad de incidente. **La prueba de usabilidad con otra persona sigue pendiente.** No despliegue públicamente el MVP sin controles de identidad, autorización y revisión de datos.
