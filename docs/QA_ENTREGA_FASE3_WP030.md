# WP-030 — QA y entrega de Fase 3

## Estado verificado el 2026-11-23

WP-025 a WP-030 se integraron mediante PR individuales en `integration/sentrix-phase3`. Los resultados de la rama integrada y los SHA de cada merge constan en el [registro de integración](INTEGRACION_FASE3_WP025_WP030.md).

| Comprobación | Resultado |
|---|---|
| Regresión local | 98 tests correctos sobre el merge WP-030; 10 AppTests omitidos por ausencia de Streamlit local. |
| Regresión Docker endurecido | 98/98 correctos sobre el merge WP-030 de la rama integrada, red deshabilitada, raíz de solo lectura y montajes mínimos de solo lectura. |
| P01 / P02 / P03 | 7/7, 8/8 y 12/12; ejecutores informaron originales sin cambios. |
| E2E Docker aislado | PASS sobre la rama integrada; HTTP, decisión en SQLite tras reinicio y flujo AppTest. Proyecto `kenworth-wp012-e2e-0afef051`, puerto efímero 62818; se detuvo sin borrar el volumen. |
| Demo nueva | `127.0.0.1:18531` HTTP 200 desde la rama integrada. Sidecar sin puertos publicados: dos Syslog sintéticos → dos eventos canónicos → dos alertas provisionales. |
| Demo estable | `127.0.0.1:18513` HTTP 200; no se modificó ni detuvo. |
| Seguridad | App y sidecar como `appuser`, raíz de solo lectura, `cap_drop: ALL`, `no-new-privileges`, tmpfs y límites. App publicada solo en loopback; sidecar sin publicación de puertos. |
| Recursos | Muestra instantánea de app: 35,86 MiB / 768 MiB, CPU 0,00 %; sidecar: 14,8 MiB / 384 MiB, CPU 0,24 %. No es benchmark de carga. |
| IA | Fallback determinista mediana 17,97 ms (3 rondas), pico 68,2 KiB de asignaciones Python; ningún modelo CPU real probado. |

Las pruebas usan datos sintéticos y no atacan al host Windows. El ejecutor E2E monta solo `src`, `tests`, `.streamlit` y los recursos de prueba, en modo de solo lectura y sin red para AppTest. Las evidencias extensas locales se guardan bajo `artifacts/acceptance/`, excluido de Git.

## Controles no comprobados y límites

- Docker no garantiza aislamiento absoluto del host. No se efectuó prueba de escape ni ataque al anfitrión.
- La red bridge conserva egress; no se verificó una política de bloqueo saliente. El perfil de colector no publica puerto a host/LAN.
- No se ejecutó escaneo de vulnerabilidades de imagen o dependencias; no se certifica seguridad de producción.
- El volumen SQLite no tiene cuota física impuesta por Docker. El pipeline mantiene un máximo lógico de eventos y el receptor aplica retención y backpressure con rechazo explícito.
- Los perfiles Administrador, Analista y Observador son etiquetas de demostración sin login ni identidad confiable.
- El proveedor IA local requiere infraestructura explícita en el mismo espacio de red. No se descargó ni midió un modelo CPU; proveedores externos siguen apagados por defecto.
- Las alertas del colector se muestran como conteos persistidos en Panorama; la investigación detallada sigue centrada en el archivo sintético de Fase 2.
- No se probaron accesibilidad con usuarios reales, escáneres de vulnerabilidades ni ataques adversariales en VM descartable.

## Guion breve

1. Abrir **Panorama** y comprobar los 324 eventos y seis alertas del archivo sintético, más el estado persistido del colector opt-in.
2. Abrir **Operaciones**: prioridades, recomendaciones, bandeja de revisión y perfiles de demostración sin autoridad real.
3. Seguir una alerta en **Topología**: activo, relación con evidencia, hallazgo y propuesta; distinguir `allow`, `deny` y documental.
4. Generar un borrador en **Asistente IA**; mostrar proveedor `fallback`, evidencia y revisión humana.
5. Ejecutar dos mensajes `--canonical` dentro del sidecar y mostrar dos eventos y dos alertas provisionales, luego reiniciar el sidecar y comprobar persistencia.
6. Registrar una decisión justificada en **Alertas** y explicar que no ejecuta contención.

## Próxima puerta de gobierno

Los PR WP-025 a WP-030 ya se fusionaron a `integration/sentrix-phase3` en orden, con HEAD fijado y regresión posterior. Preparar el PR final de fase hacia `main` y dejarlo abierto. El propietario debe autorizar específicamente cualquier merge final a `main`.
