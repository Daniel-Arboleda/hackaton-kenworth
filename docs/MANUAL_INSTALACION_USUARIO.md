# Instalación y manual de usuario

## Requisitos de infraestructura

- Equipo local con Docker Desktop, Docker Compose, PowerShell y un puerto loopback libre. Python 3.10+ permite ejecutar las pruebas unitarias sin la imagen; la imagen usa Python 3.12.
- Recursos sintéticos `Kenworth_Recursos_de_Prueba/` presentes en este repositorio. No sustituirlos por datos reales ni editar sus originales para la demostración.
- La primera construcción puede requerir red para obtener la imagen base y dependencias fijadas en `requirements.txt`. La ejecución normal del dashboard no requiere servicios externos.
- Espacio para la imagen y un volumen SQLite por proyecto Compose. No se declara una capacidad empresarial ni una cifra mínima de hardware que no se haya medido.

## Arranque, salud y detención

```powershell
$env:PORT = '18513'
docker compose -p kenworth-demo -f .\compose.yaml config
docker compose -p kenworth-demo -f .\compose.yaml up --build -d
docker compose -p kenworth-demo -f .\compose.yaml ps
(Invoke-WebRequest 'http://localhost:18513/_stcore/health').StatusCode
```

Abra `http://localhost:18513`. Si el puerto está ocupado, seleccione otro en `PORT` antes de iniciar. Si la aplicación no carga, revise `docker compose -p kenworth-demo -f .\compose.yaml logs --tail 100`. Detenga con `docker compose -p kenworth-demo -f .\compose.yaml down`; no use `down -v` si necesita conservar decisiones. El nombre de proyecto aísla red y volumen de otros worktrees. No exponga el puerto fuera de localhost: el MVP no tiene autenticación.

Si Docker no puede crear otra subred por agotamiento de pools, use el override incluido que conecta solo este contenedor al `bridge` ya existente:

```powershell
$env:PORT = '18513'
docker compose -p kenworth-demo -f .\compose.yaml -f .\compose.bridge.yaml config
docker compose -p kenworth-demo -f .\compose.yaml -f .\compose.bridge.yaml up --build -d
docker compose -p kenworth-demo -f .\compose.yaml -f .\compose.bridge.yaml ps
docker compose -p kenworth-demo -f .\compose.yaml -f .\compose.bridge.yaml down
```

Mantenga el mismo nombre `kenworth-demo` para reutilizar su volumen. El override no borra ni cambia redes o volúmenes ajenos; **no ejecute `down -v`**. La prueba E2E WP-012 emplea la misma estrategia en un proyecto temporal aislado.

## Recorrido de analista

1. **Resumen:** compruebe los conteos del dataset y la cola agrupada. “Con decisión humana” se calcula desde SQLite, por lo que puede variar entre entornos.
2. **Prioridades:** abra la primera investigación. Lea impacto, exposición, evidencia, acción propuesta y estado. La prioridad no equivale a severidad de incidente.
3. **Riesgos por activo:** seleccione DB-LAB para ver criticidad, zona, rol propuesto, H01–H04, relaciones, políticas registradas y prioridad backend.
4. **Alertas:** filtre y seleccione AL001. Consulte E0321, R03, BACKUP-LAB y CH01; lea la explicación y el playbook. CH01 es contexto y no cierra la alerta automáticamente.
5. **Decisión humana:** elija estado, disposición y rol destinatario; escriba justificación. Al guardar, SQLite conserva el registro. “Rol destinatario” no envía aviso. El cierre exige disposición de actividad justificada o posible falso positivo y una justificación.
6. **Topología:** compare `allow` observado, `deny` y documental no verificado. Consulte IDs de eventos de cada relación; no deduzca una ruta transitable de `deny`.
7. **Rutas hipotéticas:** seleccione una candidata y lea tramos y condiciones no verificadas. El análisis administrativo se muestra separado como no evaluable con evidencia actual.
8. **Hardening:** revise H01, H02 y H05, acción, impacto cualitativo, verificación, reversión y rol propuesto. No se ejecuta ningún cambio.
9. **Reporte:** descargue Markdown generado en memoria. Revise las justificaciones que una persona haya introducido antes de compartir el archivo. La sección **Validación** explica P01 y muestra evidencia local solo si está disponible.

## Recuperación y pruebas

El volumen `kenworth-demo_decisions` conserva las decisiones al reiniciar el mismo proyecto Compose. Cambiar el nombre de proyecto crea un volumen diferente. No copie ni borre volúmenes de otros entornos. Para una prueba aislada de persistencia use `.\scripts\test-e2e.ps1`, que asigna proyecto, puerto y volumen propios. P01/P02/P03 no escriben en recursos originales; generan evidencia bajo `artifacts/acceptance/`.

Las instrucciones de ejecución y resultados esperados están en [VALIDACION_WP012.md](VALIDACION_WP012.md). La prueba de facilidad de uso con otra persona está **pendiente**; el protocolo de seis pasos figura allí. Un AppTest aprobado no sustituye esa prueba humana.
