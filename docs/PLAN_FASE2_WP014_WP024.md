# Plan maestro de fase 2 — WP-014 a WP-024

## Objetivo y baseline

Ampliar el MVP local sobre datos exclusivamente sintéticos, conservando el monolito Python, Streamlit, Docker y SQLite. La rama `integration/kenworth-phase2` parte de `main` `7a7b867a992681b2ae4f7184328cd1decf3fa6db` (23 de noviembre de 2026). Los PR #4–#11 de fase 1 figuran fusionados. La demo de `main` en puerto 18513 y los worktrees ajenos quedan fuera de esta fase.

Baseline comprobado en la rama aislada: 44/44 pruebas en Docker; P01 7/7, P02 8/8, P03 12/12, Compose válido; recursos originales sin cambios. En Python local se omiten siete pruebas que requieren Streamlit. Un HTTP 200 por sí solo no sustituye las pruebas.

## Arquitectura, contratos y compatibilidad

WP-014 fija interfaces Python y contratos JSON serializables para fuentes, parsers, eventos normalizados, auditorías, hallazgos, propuestas de calibración, proveedores de IA, herramientas y borradores de investigación. El trabajo posterior debe conservar los contratos de `ingestion`, `detection`, `correlation`, `topology`, `exposure`, `prioritization`, `storage` y `reports`, y no modificar P01/P02/P03 para ocultar regresiones. Los especialistas documentan sus módulos en archivos propios; este registro lo actualiza solo el integrador.

| WP | Dependencia | Alcance y criterio de aceptación | Rama | PR / HEAD / merge | Pruebas y evidencia | Estado |
|---|---|---|---|---|---|---|
| 014 | Baseline | Interfaces, esquemas, validación, compatibilidad y ADR | `agent/architecture/wp_014` | PR #12, HEAD `5da3630`, merge `bc77553c584750747c72908d32830e68ddea7323` | 49/49 Docker; P01 7/7, P02 8/8, P03 12/12 | INTEGRADO_EN_FASE2 |
| 015 | 014 | Navegación, componentes, estados y dashboard profesional | `agent/frontend_ux/wp_015` | PR #15, HEAD `f7cbc42`, merge `0c2968a7322a1dcfe1f47c5c6c860bd5a01895b7` | 50/50 Docker en rama; 67/67 conjunta tras PR #17 | INTEGRADO_EN_FASE2 |
| 016 | 014, 015 | Grafo interactivo con procedencia y leyenda | `agent/topology_visual/wp_016` | PR #18, HEAD `f321964`, merge `d762cad4f2e474b00e2926d7ec3737555a45b7f2` | 72/72 Docker post-merge; P01 7/7, P02 8/8, P03 12/12 en rama | INTEGRADO_EN_FASE2 |
| 017 | 014 | Academia, ayuda contextual y borradores locales aislados | `agent/academy/wp_017` | PR #13, HEAD `3ae966d`, merge `9cf883912ef13b4b8e457f71782009a7abb552b9` | 53/53 Docker post-merge; P01 7/7, P02 8/8, P03 12/12 | INTEGRADO_EN_FASE2 |
| 018 | 014 | Auditorías y calibración local controlada | `agent/audit_engineer/wp_018` | PR #16, HEAD `58f9f76`, merge `ca3572b395047b0cded0c13e5c886fe71ef11d39` | 58/58 Docker en rama; 9/9 específicos post-merge; 67/67 conjunta | INTEGRADO_EN_FASE2 |
| 019 | 014 | Receptor Syslog TCP loopback y fuente continua sintética | `agent/ingestion_engineer/wp_019` | PR #14, HEAD `bcbf292`, merge `ea24e0b9c742e7defc43dae72fc754add0ecfe28`; corrección PR #17, HEAD `b5c1094`, merge `fdb6ca992a9a1598cefed2b7239732f3df46cfdd` | 57/57 Docker tras PR #14; 67/67 conjunta tras corrección de orden | INTEGRADO_EN_FASE2 |
| 020 | 014, 019 | Parsers agnósticos y fixtures Palo Alto | `agent/parser_engineer/wp_020` | PR #20, HEAD `ad5ba4b`, merge `5d0fed333fb0693c54cccfc0f1961716666de3ab` | 78/78 Docker post-merge; P01 7/7, P02 8/8, P03 12/12 en rama | INTEGRADO_EN_FASE2 |
| 021 | 014 | Asistente intercambiable, herramientas read-only y fallback | `agent/ai_engineer/wp_021` | PR #21, HEAD `394c4f9`, merge `573bc24c371d50090286300338feb33e87c00ad9` | 86/86 Docker post-merge; adaptadores externos simulados | INTEGRADO_EN_FASE2 |
| 022 | 015–021 | Flujos funcionales A–F sin perder MVP | `agent/integration_engineer/wp_022` | PR #22, HEAD `85b19a5`, merge `4ee41202d4eb0716b2a6e50cd305289763b6384a` | 89/89 Docker post-merge; P01 7/7, P02 8/8, P03 12/12 en rama | INTEGRADO_EN_FASE2 |
| 023 | 022 | QA, seguridad, visual y E2E aislado | `agent/qa_engineer/wp_023` | PR #23, HEAD `4b831a7`, merge `cbc6f28a55981803c84e4fcf5c971ff87df9f32f` | 90/90 Docker post-merge; P01 7/7, P02 8/8, P03 12/12; visual en navegador | INTEGRADO_EN_FASE2 |
| 024 | 023 | Documentación, informe y PR final a `main` | `agent/release_engineer/wp_024` | PR #24, HEAD `521a030`, merge `c1b83fb2e9c9f05105f3f14d59bead4556bb0e41` | 90/90 Docker post-merge; P01 7/7, P02 8/8, P03 12/12 en rama; enlaces válidos | INTEGRADO_EN_FASE2; PR FINAL PENDIENTE |

## Integración y decisiones

Cada WP tiene worktree y rama exclusivos, commit, push HTTPS y PR dirigido a `integration/kenworth-phase2` cuando hay cambios reales. Antes de fusionar en la rama de fase: verificar HEAD, alcance, checks, reviews, protección, mergeability y pruebas ejecutadas; luego regresión post-merge y registrar SHA. Los WPs dependientes parten del contrato integrado, no de una referencia obsoleta. El PR final de `integration/kenworth-phase2` a `main` se prepara para revisión y **no se fusiona sin aprobación específica del propietario**.

Decisiones iniciales: conservar fuentes y datos originales en solo lectura; no conectar dispositivos reales; no exponer servicios fuera de loopback; no instalar modelos automáticamente; proveedor de IA externo deshabilitado por defecto; ninguna alerta equivale a incidente confirmado; acciones y calibraciones empresariales exigen identidad y aprobación humana verificables.

## Riesgos, bloqueos y evidencias

Riesgos conocidos: la demo no tiene autenticación empresarial; Docker agotó pools de subred en este equipo y dispone de `compose.bridge.yaml` local; el usuario humano de la prueba de usabilidad sigue pendiente. Esos hechos no bloquean diseño y pruebas sintéticas, pero impiden declarar preparación productiva. No se observó rama publicada verificable de Alejandra al iniciar la fase; no se modifica ni fusiona su trabajo.

Las evidencias locales de aceptación van en `artifacts/acceptance/`, excluidas de Git. Este archivo registra estados verificables; `IMPLEMENTADO`, `PROBADO` e `INTEGRADO_EN_FASE2` son estados distintos. Los informes de cada especialista contienen los detalles de sus pruebas y limitaciones.
