# Dependencias, licencias y evolución

## Dependencias y empaquetado

El código de negocio usa la biblioteca estándar de Python 3.12 en la imagen Docker. Streamlit 1.40.2 proporciona la UI y AppTest. `requirements.txt` fija la versión de Streamlit y sus dependencias de instalación, entre ellas pandas, Altair y pyarrow; no se añadió una biblioteca de grafos, un modelo de IA ni un servicio externo. `Dockerfile` instala ese archivo, copia `src/`, ejecuta como usuario no privilegiado y no empaqueta los recursos originales dentro de la imagen: Compose los monta en modo solo lectura.

**Licencias:** el repositorio no incluye todavía un archivo `LICENSE` propio. Por ello, no se presume una autorización de redistribución del código o de los recursos. Antes de entregar públicamente un paquete o imagen, el propietario debe definir la licencia del proyecto y revisar las licencias y avisos de todas las dependencias fijadas. Esta documentación no sustituye esa revisión jurídica y no atribuye licencias no verificadas.

## Requisitos y límites operativos

El MVP se ejecuta localmente en un solo contenedor, con puerto de loopback y volumen SQLite. No tiene autenticación ni autorización por usuario, cifrado de base por aplicación, ingestión de dispositivos reales, retención configurable ni copias de seguridad automatizadas. No se midieron capacidad máxima, carga concurrente o disponibilidad. La revisión de seguridad WP-012 es local y no equivale a auditoría externa ni análisis completo de dependencias.

## Evolución empresarial propuesta

1. Acordar con el cliente fuentes de datos reales, clasificación de información, retención y consentimiento; conservar el laboratorio aislado.
2. Definir identidad y permisos por rol, registro de auditoría y manejo de secretos antes de cualquier despliegue no local.
3. Validar con responsables reales horarios, umbrales, reglas, inventario y criterios de cierre; medir falsos positivos y cobertura con datos autorizados.
4. Integrar cambios de firewall y tickets solo mediante procesos de aprobación, controles y evidencia de ejecución; separar siempre propuesta de acción aplicada.
5. Verificar dependencias, licencia, gestión de parches, respaldo de SQLite o migración justificada, monitoreo y pruebas de carga.
6. Ejecutar la prueba de usabilidad pendiente con otra persona y registrar resultados reales antes de declarar la experiencia validada.

Ninguna de estas medidas forma parte del funcionamiento actual ni autoriza acceder a infraestructura de Kenworth.
