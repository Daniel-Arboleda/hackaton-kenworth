# SENTRIX — plan de ejecución de Fase 3

Base verificada: `origin/main` `7822ad3a1b7f2f5d81be483917a6a06777007a5f` (Fase 2 integrada). Rama de fase: `integration/sentrix-phase3`. La demo estable y los recursos sintéticos permanecen intactos. Cada WP usa rama y worktree propios, pruebas, documentación, PR a la rama de fase, revisión y regresión posterior. El PR final a `main` se deja abierto sin fusionar.

| WP | Dependencia | Resultado esperado | Rama | PR / HEAD / merge | Pruebas | Estado |
|---|---|---|---|---|---|---|
| 025 | Base Fase 2 | Endurecimiento del laboratorio y modelo de amenazas verificable | `agent/security/wp_025` | Pendiente | Regresión Docker, Compose y controles efectivos | ACTIVO |
| 026 | 025 | Centro de operaciones y perfiles didácticos sin login | `agent/operations/wp_026` | Pendiente | Navegación, decisiones, notificaciones internas | PENDIENTE |
| 027 | 025 | Orquestador IA-first con fallback y benchmark sintético | `agent/assistant/wp_027` | Pendiente | Evidencia, seguridad, CPU, RAM, latencia | PENDIENTE |
| 028 | 025, 027 | Flujo continuo local y persistente | `agent/continuous/wp_028` | Pendiente | TCP loopback, reinicio, backpressure, E2E | PENDIENTE |
| 029 | 026–028 | Grafo y UX de investigación guiada | `agent/topology_ux/wp_029` | Pendiente | Recorrido y procedencia | PENDIENTE |
| 030 | 025–029 | QA, evidencia y entrega | `agent/release/wp_030` | Pendiente | Regresión, P01/P02/P03, Docker, demo | PENDIENTE |

Restricciones: no leer datos del host ajenos al repositorio, no montar socket Docker ni rutas personales, no ejecutar pruebas hostiles en Windows, no usar datos reales ni credenciales externas, no exponer puertos a LAN/Internet. Los perfiles de demostración no autentican ni aprueban cambios reales. Los controles de Docker, red y host se informan por separado; ninguno implica aislamiento absoluto.
