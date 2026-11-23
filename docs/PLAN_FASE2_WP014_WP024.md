# Plan maestro de fase 2 — WP-014 a WP-024

## Objetivo y baseline

Ampliar el MVP local sobre datos exclusivamente sintéticos, conservando el monolito Python, Streamlit, Docker y SQLite. La rama `integration/kenworth-phase2` parte de `main` `7a7b867a992681b2ae4f7184328cd1decf3fa6db` (23 de noviembre de 2026). Los PR #4–#11 de fase 1 figuran fusionados. La demo de `main` en puerto 18513 y los worktrees ajenos quedan fuera de esta fase.

Baseline comprobado en la rama aislada: 44/44 pruebas en Docker; P01 7/7, P02 8/8, P03 12/12, Compose válido; recursos originales sin cambios. En Python local se omiten siete pruebas que requieren Streamlit. Un HTTP 200 por sí solo no sustituye las pruebas.

## Arquitectura, contratos y compatibilidad

WP-014 fija interfaces Python y contratos JSON serializables para fuentes, parsers, eventos normalizados, auditorías, hallazgos, propuestas de calibración, proveedores de IA, herramientas y borradores de investigación. El trabajo posterior debe conservar los contratos de `ingestion`, `detection`, `correlation`, `topology`, `exposure`, `prioritization`, `storage` y `reports`, y no modificar P01/P02/P03 para ocultar regresiones. Los especialistas documentan sus módulos en archivos propios; este registro lo actualiza solo el integrador.

| WP | Dependencia | Alcance y criterio de aceptación | Rama | PR / HEAD / merge | Pruebas y evidencia | Estado |
|---|---|---|---|---|---|---|
| 014 | Baseline | Interfaces, esquemas, validación, compatibilidad y ADR | `agent/architecture/wp_014` | Pendiente | Contratos y regresión P01/P02/P03 | PENDIENTE |
| 015 | 014 | Navegación, componentes, estados y dashboard profesional | `agent/frontend_ux/wp_015` | Pendiente | AppTest, accesibilidad y regresión | PENDIENTE |
| 016 | 014, 015 | Grafo interactivo con procedencia y leyenda | `agent/topology_visual/wp_016` | Pendiente | Nodos, filtros, evidencia y rutas | PENDIENTE |
| 017 | 014 | Academia, ayuda contextual y borradores locales aislados | `agent/academy/wp_017` | Pendiente | Estado de formularios y límites de acceso | PENDIENTE |
| 018 | 014 | Auditorías y calibración local controlada | `agent/audit_engineer/wp_018` | Pendiente | Estados, R03, invariantes y reversión | PENDIENTE |
| 019 | 014 | Receptor Syslog TCP loopback y fuente continua sintética | `agent/ingestion_engineer/wp_019` | Pendiente | Recepción, límites, deduplicación y recuperación | PENDIENTE |
| 020 | 014, 019 | Parsers agnósticos y fixtures Palo Alto | `agent/parser_engineer/wp_020` | Pendiente | Detección de formato, trazabilidad y errores | PENDIENTE |
| 021 | 014 | Asistente intercambiable, herramientas read-only y fallback | `agent/ai_engineer/wp_021` | Pendiente | Mock local, allowlist, inyección y límites | PENDIENTE |
| 022 | 015–021 | Flujos funcionales A–F sin perder MVP | `agent/integration_engineer/wp_022` | Pendiente | Integración y regresión | PENDIENTE |
| 023 | 022 | QA, seguridad, visual y E2E aislado | `agent/qa_engineer/wp_023` | Pendiente | 44 baseline, P01/P02/P03 y nuevas suites | PENDIENTE |
| 024 | 023 | Documentación, informe y PR final a `main` | `agent/release_engineer/wp_024` | Pendiente | Reproducción y revisión | PENDIENTE |

## Integración y decisiones

Cada WP tiene worktree y rama exclusivos, commit, push HTTPS y PR dirigido a `integration/kenworth-phase2` cuando hay cambios reales. Antes de fusionar en la rama de fase: verificar HEAD, alcance, checks, reviews, protección, mergeability y pruebas ejecutadas; luego regresión post-merge y registrar SHA. Los WPs dependientes parten del contrato integrado, no de una referencia obsoleta. El PR final de `integration/kenworth-phase2` a `main` se prepara para revisión y **no se fusiona sin aprobación específica del propietario**.

Decisiones iniciales: conservar fuentes y datos originales en solo lectura; no conectar dispositivos reales; no exponer servicios fuera de loopback; no instalar modelos automáticamente; proveedor de IA externo deshabilitado por defecto; ninguna alerta equivale a incidente confirmado; acciones y calibraciones empresariales exigen identidad y aprobación humana verificables.

## Riesgos, bloqueos y evidencias

Riesgos conocidos: la demo no tiene autenticación empresarial; Docker agotó pools de subred en este equipo y dispone de `compose.bridge.yaml` local; el usuario humano de la prueba de usabilidad sigue pendiente. Esos hechos no bloquean diseño y pruebas sintéticas, pero impiden declarar preparación productiva. No se observó rama publicada verificable de Alejandra al iniciar la fase; no se modifica ni fusiona su trabajo.

Las evidencias locales de aceptación van en `artifacts/acceptance/`, excluidas de Git. Este archivo registra estados verificables; `IMPLEMENTADO`, `PROBADO` e `INTEGRADO_EN_FASE2` son estados distintos. Los informes de cada especialista contienen los detalles de sus pruebas y limitaciones.