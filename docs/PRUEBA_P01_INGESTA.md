# P01 — Aceptación de ingesta y alertamiento

**Objetivo:** comprobar que el CSV sintético se valida, que entradas defectuosas se rechazan y que las seis alertas coinciden íntegramente con las referencias. **Tecnología:** Python estándar, PowerShell y `unittest`; sin servicios ni dependencias nuevas.

**Prerrequisitos:** checkout con `Kenworth_Recursos_de_Prueba`, Python 3 disponible y PowerShell. Desde cualquier ubicación, ejecute el script por su ruta; desde la raíz del worktree, el comando único es `.\scripts\test-p01.ps1`. Alternativa si la política local impide scripts: `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test-p01.ps1` para esa sesión, sin cambiar la política global. También puede ejecutar `python tests/acceptance_p01.py`. Para ejecutar toda la suite: `.\scripts\test-all.ps1`.

| Caso | Entrada | Resultado esperado |
|---|---|---|
| P01-A | CSV original | 324 eventos, 324 IDs únicos, 6 alertas |
| P01-B | Sin `evento_id` | Rechazo por columna faltante |
| P01-C | ID duplicado | Rechazo por duplicado |
| P01-D | `origen_ip` vacío | Rechazo por campo obligatorio |
| P01-E | Puerto 65536 y bytes -1 | Ambos rechazados |
| P01-F | Tipo desconocido | Rechazo por tipo inválido |
| P01-G | CSV y referencias | Igualdad completa de alertas y resumen |

Cada ejecución crea `artifacts/acceptance/p01/<run_id>/results.json`, `results.csv` y `summary.txt`; `latest.txt` señala el último directorio. La evidencia no se versiona. Registra fecha, evaluador opcional (`--evaluator` en Python), versión de Python, sistema, rama, SHA, duración medida y resultado por caso. **PASS** significa comportamiento esperado, incluido un rechazo correcto; **FAIL**, diferencia o aceptación indebida; **BLOCKED**, falta de entrada. El código de salida es cero solo si no hay FAIL ni BLOCKED.

**Antecedente manual confirmado por el usuario:** primera ejecución P01-A/B/C/D aprobada en Windows PowerShell con Python 3.13.6 y worktree limpio. Se observaron 324 eventos únicos y 6 alertas. No se midieron tiempos; P01-E/F/G no formaron parte de esa ejecución manual. Las ejecuciones automatizadas se registran por separado en los artefactos locales.

**Validación automatizada inicial:** Codex (agente QA) ejecutó P01-A a P01-G el 21/11/2026 con Python 3.13.6: 7 PASS, 0 FAIL, 0 BLOCKED; 9 pruebas `unittest` aprobaron. Las duraciones medidas están en los reportes locales y no corresponden a la ejecución manual del usuario.

**Limitaciones:** laboratorio sintético; la prueba no verifica la UI, Docker ni infraestructura real. **Evaluador de ejecuciones posteriores:** se registra en el reporte si se proporciona; de otro modo figura sin asignar. **Conclusión:** usar los resultados generados por cada ejecución para aceptar o rechazar la ingesta; no extrapolar a incidentes reales.
