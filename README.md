# Kenworth Security Monitor

MVP local Streamlit para el laboratorio sintético Estud-IA. No representa infraestructura ni incidentes reales de Kenworth.

## Ejecutar

Instale Docker Desktop con Compose. Desde la raíz del repositorio:

```powershell
docker compose up --build -d
docker compose ps
docker compose logs --tail 100
```

Abra http://localhost:8501. Puede cambiar el puerto con `PORT` en un archivo `.env` local. Detenga con `docker compose down`; conserve el volumen `decisions` para mantener las decisiones.

## Pruebas

Con Python 3.10+ local: `python -m unittest discover -s tests`. Las pruebas usan solo la biblioteca estándar. No ejecutan el analizador entregado. El contenedor oficial excluye los tests.

## Demostración

Revise AL001 con CH01 sin cierre automático. Revise AL004 y AL005 como dos señales del mismo evento E0324. Guarde decisiones justificadas para dos alertas, muestre las tres propuestas de hardening y la prueba reproducible.

## Límites

Sin ingestión Palo Alto nativa, escaneo, CVE, confirmación automática de incidentes, IA externa ni respuesta sobre firewall. Construir la imagen puede requerir red para descargar Python y Streamlit; el uso normal de la aplicación es local.
