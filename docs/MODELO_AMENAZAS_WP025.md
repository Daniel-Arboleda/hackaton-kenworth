# WP-025 — Seguridad del laboratorio SENTRIX

## Alcance y límites

El laboratorio procesa únicamente los recursos sintéticos de `Kenworth_Recursos_de_Prueba`. Las alertas son señales para investigación, no incidentes confirmados. Este modelo cubre la aplicación y su contenedor; no certifica el aislamiento del host ni sustituye una revisión del motor Docker.

## Superficies y controles

| Superficie | Control configurado | Límite |
|---|---|---|
| Proceso | Usuario `appuser` (UID 10001), `no-new-privileges`, todas las capacidades eliminadas | El kernel y el demonio Docker siguen siendo parte de la base de confianza. |
| Escritura | Raíz del contenedor de solo lectura; `/app/data` es el único volumen persistente con escritura; `/tmp` es tmpfs de 64 MiB con `noexec,nosuid` | La base SQLite puede crecer dentro del volumen; la aplicación debe aplicar sus propios límites de retención. |
| Recursos | 1 CPU, 768 MiB de RAM y 128 procesos | Son límites del contenedor, no reservas ni garantías de rendimiento. |
| Datos | Recursos sintéticos montados en `/app/resources:ro`; `.dockerignore` excluye Git, pruebas, documentación, bases locales y recursos del contexto de construcción | No montar directorios personales, credenciales ni el socket Docker. |
| Entrada | Puerto HTTP publicado solo en `127.0.0.1`; el colector Syslog de la aplicación admite únicamente loopback y entradas acotadas | Otros procesos del host pueden acceder al puerto local. No usarlo como frontera de autenticación. |
| IA | Proveedores externos deshabilitados por defecto, transporte local limitado a loopback y herramientas de solo lectura | El operador debe revisar cualquier habilitación explícita y sus destinos. |
| Red saliente | El perfil Compose predeterminado conserva la red bridge de Docker | **No hay bloqueo verificable de salida**. Una política de egress requiere una red o entorno aislado adicional. |

## Amenazas relevantes

- Entrada malformada o voluminosa: usar límites del parser, del colector y de los adaptadores; los errores se aíslan y se registran sin ejecutar comandos.
- Inyección en logs o respuestas de IA: tratarlas como datos no confiables; las herramientas del asistente no ejecutan comandos ni modifican políticas.
- Agotamiento de disco: retención y límites de aplicación; supervisar el volumen `decisions` durante la demostración.
- Compromiso del proceso: las restricciones reducen privilegios y escritura, pero no prueban que una fuga del contenedor sea imposible.
- Exposición de red: el enlace HTTP es loopback; la red saliente del contenedor no está bloqueada.

## Verificación segura

Comprobar `docker compose config` y el `docker inspect` de **un contenedor SENTRIX aislado** para confirmar usuario, capacidades, raíz de solo lectura, límites y enlaces de puerto. Ejecutar la regresión sintética dentro de un contenedor aislado. No probar escapes, ataques al host ni secretos personales. Si se necesita una prueba adversarial del aislamiento, usar una VM descartable sin cuentas, sesiones, secretos o montajes compartidos.

## Riesgos pendientes

No se ha verificado un bloqueo de egress, un escaneo de vulnerabilidades de la imagen ni un límite del volumen persistente impuesto por Docker. El archivo `compose.bridge.yaml` no aporta aislamiento de salida. Mantener las integraciones externas desactivadas por defecto.

## Evidencia de verificación (2026-11-23)

- `docker compose config --quiet`: correcto.
- Contenedor aislado `sentrix-wp025-app-1`: `ReadonlyRootfs=true`, `CapDrop=[ALL]`, `PidsLimit=128`, `Memory=805306368`, `NanoCpus=1000000000`, `SecurityOpt=[no-new-privileges:true]`, usuario `appuser`, `/tmp` con `noexec,nosuid` y puerto `8501/tcp` enlazado a `127.0.0.1:18525`.
- Salud HTTP de la aplicación: 200 en loopback.
- `python -m unittest discover -s tests -q`: 90 pruebas locales correctas; 10 omisiones de Streamlit por entorno local.
- Regresión en imagen Docker con `--network none`, raíz de solo lectura y montajes limitados a `src`, `tests`, `.streamlit` y recursos sintéticos del repositorio: 90/90 correctas.
