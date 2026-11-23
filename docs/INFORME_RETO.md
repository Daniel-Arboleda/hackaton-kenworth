# Informe del reto — Kenworth Security Monitor

## Problema y usuario objetivo

Un equipo de TI pequeño necesita ordenar señales heterogéneas y decidir qué revisar primero, con contexto suficiente para distinguir una anomalía de una actividad posiblemente autorizada. El MVP está dirigido a un analista que investiga y documenta una decisión, con administrador del activo y responsable de Tecnología como roles propuestos para revisión y escalamiento. Estos roles no son asignaciones confirmadas por Kenworth.

## Solución demostrada en laboratorio

El monolito Python y Streamlit ingiere 324 eventos sintéticos, genera seis alertas con cuatro reglas, relaciona diez activos y políticas descriptivas, conserva 103 relaciones observadas y tres flujos documentados no verificados. Ofrece explicaciones, playbooks, rutas candidatas prudentes, una matriz de prioridad de revisión 1–9, tres acciones preventivas y un registro SQLite de decisiones humanas. El dashboard no actúa sobre dispositivos ni crea incidentes automáticamente.

### Señales justificadas por evidencia

| Señal | Evidencia | Interpretación y siguiente paso |
|---|---|---|
| AL006, fallos repetidos | E0301–E0305: cinco fallos consecutivos entre 09:00 y 09:04 con mismo origen, destino DB-LAB y usuario; R02 en E0305 | Cumple la regla didáctica de cinco fallos en diez minutos. Investigar titularidad y registros de autenticación; no hay evidencia vinculada de acceso exitoso. Prioridad de revisión 9/9 para el activo, sin calificar severidad de incidente. |
| AL004, volumen para revisión | E0324 registra 85 000 000 bytes, por encima del umbral de 50 000 000 | Revisar propósito, destino externo y autorización del flujo. El volumen no confirma extracción de datos. |
| AL005, inconsistencia de registro | El mismo E0324 registra R01 con destino externo, diferente del WEB-LAB descrito para R01 | Contrastar evento, regla documentada y configuración aprobada. La diferencia no demuestra por sí sola una brecha. AL004 y AL005 son dos señales de **un evento**, agrupadas en una investigación, no dos incidentes. |

### Alerta contrastada

AL001 surge de E0321: acceso exitoso fuera del horario de prueba a BACKUP-LAB con R03 a las 02:00. CH01 coincide en activo, origen, usuario y ventana de 02:00–02:30 para una revisión programada de copia. Esa coincidencia aporta una explicación posible, **sin cerrar automáticamente AL001** ni autorizar el envío externo registrado después en E0324. El analista debe validar alcance con el responsable, revisar registros y documentar una disposición antes de cerrar o escalar. AL002 y AL003 también requieren revisión individual.

## Tres recomendaciones priorizadas

| Hallazgo | Prioridad de revisión didáctica | Acción propuesta | Verificación y reversión |
|---|---:|---|---|
| H01, DB-LAB | 9/9 | Revisar y acotar R02 por origen, destino, servicio y vigencia; habilitar registro | Comprobar flujos autorizados y registros antes/después; restaurar la regla aprobada si se afecta un flujo legítimo. |
| H02, DB-LAB | 9/9 | Planificar MFA y cuentas individuales para administración | Probar acceso nominal, MFA y recuperación; restaurar acceso administrativo aprobado bajo control de cambios si falla. |
| H05, BACKUP-LAB | 6/9 | Programar y documentar una prueba de restauración | Registrar resultado, tiempo y consistencia; conservar copia y procedimiento previo y detener ante impacto operativo. |

Las puntuaciones ordenan revisión dentro del modelo de criticidad y exposición; no son CVSS, probabilidad de ataque ni severidad de un incidente. Todas las acciones requieren aprobación humana antes de ejecutarse. El escenario R02 solo estima un efecto cualitativo posible y no modifica una regla.

## Prueba documentada y valor preventivo

P01 exige 324 eventos únicos, seis alertas y coincidencia exacta con referencias en siete casos. P02 comprueba ocho casos de correlación; P03 doce casos de exposición y prioridad. E2E arranca Docker en un entorno aislado, comprueba HTTP, guarda una decisión sintética, reinicia y verifica persistencia, navegación, reporte y hardening. Los scripts escriben resultados bajo `artifacts/acceptance/`, fuera de Git. [Procedimiento y límites de validación](VALIDACION_WP012.md).

El valor preventivo es concentrar la atención en DB-LAB y R02, conservar la evidencia de cada señal, hacer visible la incertidumbre y facilitar propuestas verificables. Queda pendiente la prueba de uso con otro integrante. El siguiente paso empresarial requeriría aprobar fuentes reales, identidades y roles, permisos, políticas de retención, controles de acceso, integración segura y un proceso de cambios; el laboratorio actual no autoriza conectar infraestructura real.
