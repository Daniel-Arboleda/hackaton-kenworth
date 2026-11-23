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
- Explorar un grafo visual con filtros y evidencia; `deny` y flujos documentales no son transitables.
- Consultar Academia, ayuda contextual, auditorías didácticas y calibración local derivada.
- Guardar y recuperar borradores de investigación aislados de las decisiones definitivas.
- Inspeccionar mensajes sintéticos con parsers CSV, JSON, Syslog y Palo Alto Traffic acotado. El receptor TCP Syslog funciona aparte en loopback.
- Obtener un borrador de explicación con evidencia mediante fallback determinista. Proveedores externos deshabilitados por defecto.

## Demo de fase 2 separada

Conserve la demo estable en 18513. Para probar esta rama en otro puerto, establezca `PORT=18523` y use otro proyecto Compose, por ejemplo `kenworth-phase2`. Compruebe `docker compose ... config` antes de `up --build -d`; `compose.bridge.yaml` sigue disponible si Docker agotó pools de red. Abra `http://127.0.0.1:18523`. Cada proyecto usa su propio volumen; no ejecute `down -v` si quiere conservar decisiones.

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
- [Plan maestro y checkpoint de fase 2](docs/PLAN_FASE2_WP014_WP024.md)
- [Entrega, costos y riesgos de fase 2](docs/ENTREGA_FASE2_WP024.md)
- [QA y evidencia de fase 2](docs/QA_FASE2_WP023.md)
- [Plan de Fase 3](docs/PLAN_FASE3_WP025_WP030.md)
- [Modelo de amenazas del laboratorio](docs/MODELO_AMENAZAS_WP025.md)
- [Centro de operaciones](docs/CENTRO_OPERACIONES_WP026.md)
- [Asistente IA-first y benchmark](docs/ASISTENTE_IA_FIRST_WP027.md)
- [Flujo continuo sintético](docs/FLUJO_CONTINUO_WP028.md)
- [Recorrido guiado del grafo](docs/GRAFO_GUIADO_WP029.md)
- [QA y entrega de Fase 3](docs/QA_ENTREGA_FASE3_WP030.md)

## Demo aislada de Fase 3

Desde esta rama, use otro proyecto y puerto loopback para conservar la demo estable:

```powershell
$env:PORT = '18530'
docker compose --profile collector -p sentrix-phase3 -f .\compose.yaml -f .\compose.bridge.yaml up --build -d app collector
docker compose --profile collector -p sentrix-phase3 -f .\compose.yaml -f .\compose.bridge.yaml exec -T collector python -m kenworth.synthetic_syslog --port 18519 --count 2 --canonical
```

Abra `http://127.0.0.1:18530`. La app muestra el estado persistido del pipeline en **Panorama**. El colector escucha solo dentro de su contenedor y no publica puertos; el generador se ejecuta dentro de ese mismo contenedor. Los mensajes y alertas de esta demo son sintéticos. El perfil `collector` es opt-in y no conecta equipos reales.

## Límites

Sin conexión con Kenworth ni Palo Alto real, autenticación empresarial, escaneo, explotación, cambios de firewall, bloqueos automáticos, proveedores externos de IA en vivo, tickets externos o confirmación automática de incidentes. Un `allow` observado no prueba conectividad completa; una ruta candidata no demuestra movimiento lateral. La prioridad ordena revisión, no expresa probabilidad ni severidad de incidente. **La prueba de usabilidad con otra persona sigue pendiente.** No despliegue públicamente el MVP sin controles de identidad, autorización y revisión de datos.
