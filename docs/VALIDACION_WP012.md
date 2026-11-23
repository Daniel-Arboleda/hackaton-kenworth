# Validación integral WP-012

La validación usa exclusivamente `Kenworth_Recursos_de_Prueba`. P01 conserva siete casos y sus referencias exactas. Los ejecutores nuevos escriben JSON por caso en `artifacts/acceptance/p02/` y `p03/`; el E2E en `artifacts/acceptance/e2e/`. Estas rutas están excluidas de Git. Cada corrida P02/P03 compara hashes de todos los archivos originales antes y después.

## Ejecutar

```powershell
python -m unittest discover -s tests
.\scripts\test-p01.ps1
.\scripts\test-p02.ps1
.\scripts\test-p03.ps1
.\scripts\test-all.ps1
docker compose -f .\compose.yaml config
.\scripts\test-e2e.ps1
```

P02 verifica ocho casos: AL001/CH01, AL006, AL004 y AL005 sobre E0324, cuatro y cinco fallos, ventana mayor a diez minutos, frontera exacta y alcance restringido del cambio. P03 verifica doce casos: `allow`, `deny`, flujo documental, desconexión, nodo externo, ciclo, criticidad, evidencia ausente, hipótesis vertical no evaluable, R02/DB-LAB, orden determinista y agrupación sin incidentes inventados.

El ejecutor E2E crea un nombre Compose, puerto libre y volumen SQLite exclusivos. Usa el `bridge` Docker existente porque este equipo agotó los pools para nuevas subredes; no altera las redes, volúmenes ni decisiones de otros proyectos. Comprueba HTTP 200 de `/` y `/_stcore/health`, guarda una decisión sintética, reinicia el servicio, verifica que SQLite la conserva y ejecuta AppTest sobre navegación, reporte y hardening. Detiene el proyecto sin `-v`; el volumen de prueba queda identificado en `results.json` para inspección y no se borra automáticamente.

## Revisión de seguridad

- `compose.yaml` publica Streamlit solo en `127.0.0.1`, coherente con el MVP local sin autenticación. El contenedor conserva `no-new-privileges` y usuario no privilegiado.
- La UI no ofrece entrada para ejecutar comandos, escanear redes o aplicar cambios. Las decisiones se guardan mediante parámetros SQL; el reporte se genera en memoria y se descarga como Markdown.
- La ruta de evidencia P01 usada por la vista de validación se restringe al directorio configurado. Los recursos sintéticos se montan en Docker como solo lectura.
- No se hallaron secretos evidentes en código o datos rastreados mediante búsqueda local. Esta revisión no sustituye un análisis de dependencias ni una auditoría externa.
- Limitaciones: no hay autenticación ni autorización por usuario; los roles son propuestos, no identidades verificadas. El informe incluye justificaciones redactadas por quien opera el laboratorio y debe revisarse antes de compartirlo. No desplegar públicamente este MVP.

## Prueba con otra persona

**Pendiente de ejecución humana.** Protocolo propuesto para un integrante distinto al implementador:

1. Abrir el dashboard local y localizar la alerta AL001 sin instrucciones adicionales.
2. Identificar el evento E0321, regla R03, activo BACKUP-LAB y cambio CH01.
3. Explicar por qué CH01 no cierra automáticamente la alerta.
4. Encontrar una recomendación preventiva y su evidencia.
5. Exportar el informe Markdown y señalar una limitación del laboratorio.
6. Registrar tiempo, pasos, errores, dudas y observaciones en un acta firmada por el participante. No escribir datos reales ni decisiones definitivas sobre el volumen de demostración.

Sin participante humano disponible no se declara este protocolo como aprobado. Las pruebas automatizadas comprueban funcionalidad, no facilidad de uso real.
