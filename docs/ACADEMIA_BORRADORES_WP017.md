# Academia y borradores locales — WP-017

`kenworth.academy` contiene un glosario didáctico de 18 conceptos, ayuda contextual por grupo de pantalla y un tutorial que recorre AL001, CH01, DB-LAB y las rutas candidatas. Las definiciones distinguen evento, alerta e incidente y no atribuyen infraestructura real al cliente. `kenworth.academy_ui` expone componentes Streamlit reutilizables para que WP-022 los monte sin rehacer la navegación de WP-015.

## Recuperación de borradores

`LocalDraftStore` guarda temporalmente campos de formulario en un SQLite separado de `decisions.sqlite`. Solo se habilita con `local_demo=True`; no es un sistema de identidad empresarial. Cada operación exige un token aleatorio de 256 bits. La base almacena su hash SHA-256, no el token, y no ofrece listado global de borradores. Un ámbito no puede consultar el borrador de otro; las pruebas cubren reapertura, aislamiento y expiración. El plazo predeterminado es dos horas y el máximo es 24 horas.

El componente de UI conserva el token en el parámetro local `draft_scope` para recuperar el mismo borrador después de recargar. **Quien conozca el enlace conoce la clave de acceso al borrador:** no compartirlo. Usar solo con el dashboard enlazado a `127.0.0.1`, un volumen de demostración aislado y sin datos reales. Sin autenticación confiable no se habilitan borradores multiusuario empresariales. El integrador debe conectar los campos del formulario al componente y limpiar el borrador cuando la persona descarte o complete una decisión.

Un borrador no escribe en `kenworth.storage`, no envía notificaciones y no representa una decisión, aprobación o incidente confirmado. Los recursos originales bajo `Kenworth_Recursos_de_Prueba` nunca se usan como ubicación de escritura.

## Verificación

`python -m unittest discover -s tests` ejecuta `tests/test_academy.py`; P01/P02/P03 siguen validando los contratos existentes. Los AppTests del flujo completo se ampliarán en WP-022 y WP-023, después de conectar la navegación y el formulario.
