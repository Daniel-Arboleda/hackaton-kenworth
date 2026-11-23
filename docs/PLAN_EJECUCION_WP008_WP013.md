# Plan de ejecución WP-008 a WP-013

Registro maestro del programa sobre recursos exclusivamente sintéticos. Esta revisión se inició desde `origin/main` `8a2692576561a73ea09c6aed39a655ee01f0311e`, después de la fusión verificada de PR #4. La base de WP-010 es `02aebf47df9f3bf2a430f62fc240afc2bc7f70f0`, después de integrar WP-009 y WP-006. La base de WP-011 es `2973034fe0ffd3ecb679d7f17b35b19bdecb0da6`, tras integrar WP-010. Un estado de desarrollo no equivale a integración.

| WP | Dependencia | Criterio de aceptación | PR / SHA | Pruebas y evidencia | Estado |
|---|---|---|---|---|---|
| 008 | PR #4 | Frontend oficial en `main`, sin regresiones | PR #4; merge `8a2692576561a73ea09c6aed39a655ee01f0311e` | 20 pruebas Docker, P01 7/7, HTTP 200; regresión local post-merge aprobada | INTEGRADO |
| 006 | 008 | Explicaciones y cuatro playbooks trazables, prudentes y reproducibles | PR #6, HEAD `3776482`, merge `02aebf4` | Pruebas unitarias y regresión post-merge verificadas por integración | INTEGRADO |
| 009 | 008 | Exposición y rutas candidatas sin aristas `deny` o documentadas transitables | PR #5, HEAD `629268d`, merge `c22ae76` | 26 pruebas Docker, P01 7/7; regresión post-merge verificada por integración | INTEGRADO |
| 010 | 006 + 009 | Cola priorizada con matriz 1–3 × 1–3 y evidencia | PR #7; merge `2973034fe0ffd3ecb679d7f17b35b19bdecb0da6` | Regresión post-merge verificada por integración | INTEGRADO |
| 011 | 010 | Dashboard proactivo, reportes y AppTest | Rama `agent/frontend_proactive/wp_011`; PR y HEAD al cierre | `tests/test_frontend.py`, `tests/test_reports.py`; suite Docker y P01 | EN DESARROLLO |
| 012 | 011 | P01, P02, P03, E2E y revisión de seguridad | Pendiente | Evidencia aislada y reproducible | PENDIENTE |
| 013 | 012 | Documentación final y guion demostrable | Pendiente | Regresión final y evidencia | PENDIENTE |

## Riesgos y bloqueos

- No se observó una rama publicada verificable de Alejandra durante WP-008. Su trabajo no fue modificado ni fusionado.
- Los cuatro tests Streamlit se omiten en Python local sin la dependencia; se ejecutaron y aprobaron en Docker en WP-008.
- No hay checks registrados en PR #4; cero checks no se interpretó como pruebas aprobadas. Se ejecutaron pruebas locales y Docker explícitamente.
- Para WPs pendientes, cada PR requiere verificación de HEAD, checks, revisiones, protección, mergeability y regresión post-merge antes de marcar INTEGRADO.

## Procedencia

La evidencia P01 post-merge está en `artifacts/acceptance/p01/` del worktree de validación, excluida de Git. El repositorio conserva solo recursos de prueba bajo `Kenworth_Recursos_de_Prueba`; los originales no se editan.
