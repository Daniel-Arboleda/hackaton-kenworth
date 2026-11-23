# ADR-001 — Monolito modular y adaptadores

**Estado:** Aceptada para fase 2. **Fecha:** 2026-11-23.

## Contexto

La fase 1 funciona como un monolito Python con Streamlit, SQLite y Docker. La fase 2 incorpora fuentes continuas, auditorías e IA, pero no hay evidencia de escala o aislamiento que exija microservicios.

## Decisión

Mantener el monolito modular. Separar contratos y lógica de eventos, fuentes, parsers, reglas, investigaciones, activos, topología, riesgos, auditorías, calibración, IA, autorización y presentación. Una interfaz se define en `contracts_v2.py` antes de implementar adaptadores. El colector continuo deberá ejecutarse fuera del ciclo de renderizado Streamlit, aunque pertenezca al mismo repositorio.

## Consecuencias

Se reutilizan pruebas y APIs de fase 1 sin migración destructiva. Los WPs pueden avanzar por módulos y PR independientes. SQLite sigue siendo suficiente para decisiones locales; una necesidad futura de concurrencia o control empresarial requeriría medición y una decisión nueva. No se añade servicio ni dependencia de infraestructura por estética.
