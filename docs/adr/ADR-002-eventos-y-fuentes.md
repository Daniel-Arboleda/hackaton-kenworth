# ADR-002 — Fuente, parser y evento canónico

**Estado:** Aceptada para fase 2. **Fecha:** 2026-11-23.

## Contexto

P01 fija doce campos, 324 eventos y seis alertas. Syslog y otros formatos pueden carecer de campos o incluir datos sin equivalencia directa. Un mapeo silencioso podría producir detecciones falsas.

## Decisión

Separar `EventSource` (entrega mensajes y salud) de `LogParser` (identifica por criterios y normaliza o rechaza). `NormalizedEvent` mantiene los doce campos canónicos de fase 1 y añade metadatos de procedencia; la conversión a `detect` usa `to_legacy_dict`. Una normalización incompleta devuelve `REJECTED` o `UNMAPPED`, con explicación. Preservar campos originales y no mapeados, límites de tamaño y IDs de evidencia. No usar un LLM como parser primario.

## Consecuencias

Los parsers nuevos requieren fixtures sintéticos y pruebas de mapeo por formato. P01/P02/P03 permanecen intactos. Una regla `allow` o un log de seguridad no se interpreta como compromiso. La recepción continua queda restringida a loopback por defecto; ninguna interfaz de lectura API habilita destinos arbitrarios.
