# Práctica 1.7 — Autenticación JWT, rotación y scopes

**Autor:** Darius Joanito Marinescu

TaskFlow incorpora registro, login y JWT de acceso de 30 minutos. La actualización añade refresh tokens de un solo uso, detección de reutilización y autorización por scopes y roles.

## Arranque

Desde la carpeta `taskflow-api`, en una terminal CMD:

```cmd
python -m venv venv
venv\Scripts\activate
python -m pip install -r requirements.txt
python -c "import secrets; print(secrets.token_hex(32))"
set "TASKFLOW_SECRET_KEY=PEGA_AQUI_LA_CLAVE_GENERADA"
python -m uvicorn app.main:app --reload
```

El comando de Python genera una clave. Hay que copiarla y sustituir `PEGA_AQUI_LA_CLAVE_GENERADA` antes de arrancar el servidor. La clave debe tener al menos 32 bytes.

Una vez iniciado, la documentación interactiva está disponible en:

```text
http://127.0.0.1:8000/docs
```

El arranque crea las nuevas tablas `user_roles` y `refresh_tokens`. Los usuarios existentes y los datos del CRUD se conservan. La tabla `users` mantiene el esquema anterior.

## Archivos y responsabilidades

| Archivo | Responsabilidad |
|---|---|
| `app/security.py` | Hashing, JWT, dependencia de usuario y rotación transaccional. |
| `app/roles.py` | Relación de roles con los scopes permitidos. |
| `app/routers/auth.py` | Registro, login y renovación. |
| `app/manage_users.py` | Asignación local de roles. |
| `app/models.py` | Entidades CRUD, cuenta, rol y estado de refresh tokens. |
| `app/schemas.py` | Validación y contratos de respuesta. |
| `app/routers/tasks.py` | CRUD con scopes de tareas. |
| `app/routers/projects.py` | CRUD con scopes de proyectos. |
| `app/routers/categories.py` | CRUD con scopes de categorías. |
| `app/database.py` | Conexiones SQLite, claves foráneas y sesión por petición. |
| `app/main.py` | Arranque, middleware y registro de routers. |

## Cobertura de la rúbrica

| Criterio de excelente | Implementación | Cómo demostrarlo |
|---|---|---|
| Sal única y coste documentado | bcrypt con sal aleatoria y coste 12. | Comparar las sales de dos cuentas con la misma contraseña. |
| Refresh token y rotación | Secreto de un solo uso, sustitución atómica y revocación de familia al reutilizarlo. | Renovación y reutilización en Swagger. |
| Dependencias anidadas y scopes por rol | `Security` → `get_current_user` → `OAuth2PasswordBearer` y `get_db`. Se comprueban los scopes del token y el rol actual. | `viewer` obtiene 200 al leer y 403 al escribir. |
| 401 y `WWW-Authenticate` | Token ausente, inválido, caducado o revocado devuelve 401 con `Bearer`. | Prueba de expiración y cabecera `Bearer`. |
| Mensajes genéricos | Login erróneo usa el mismo mensaje. Registro nuevo y duplicado tienen el mismo contrato público. | Registro repetido y pruebas de login. |
| Análisis de amenazas | Amenazas y mitigaciones documentadas más abajo. | Revisión de esta documentación y del código. |

## Registro y contraseñas

`POST /auth/register` recibe `username` y `password`. El servidor calcula un hash con `passlib[bcrypt]` y asigna el rol `member`. El cliente no puede escoger un rol mediante este endpoint.

bcrypt genera una sal aleatoria en cada hash. El coste configurado es **12**, equivalente a un factor de trabajo exponencial de \(2^{12}\). Se limita la entrada a 72 bytes UTF-8 y se rechazan bytes nulos para evitar entradas incompatibles o truncadas.

La cuenta conserva un `username` único. El registro devuelve **201** con el mismo mensaje genérico si el nombre es nuevo o ya está utilizado. Repetir el registro no modifica la contraseña de la cuenta existente.

El 201 de este contrato no permite confirmar al cliente si se insertó una nueva fila.

## Login y JWT

`POST /auth/login` recibe un formulario OAuth2 con `username`, `password` y `scope` opcional. Un login válido devuelve:

```json
{
  "access_token": "<JWT de acceso>",
  "token_type": "bearer",
  "refresh_token": "<secreto de renovación>",
  "expires_in": 1800,
  "scope": "categories:read categories:write projects:read projects:write tasks:read tasks:write"
}
```

El JWT usa **HS256** e incorpora:

- `sub`: usuario al que pertenece el token.
- `iat`: momento de emisión.
- `exp`: momento de expiración.
- `jti`: identificador del token.
- `type`: tipo de token.
- `scope`: permisos concedidos.
- `sid`: identificador de la familia de sesión.

La validación fija el algoritmo permitido y exige `exp` y `sub`, tipo `access`, sesión válida y usuario existente.

Los errores de usuario inexistente y contraseña incorrecta devuelven el mismo **401** y ejecutan una comprobación bcrypt. Las respuestas con tokens incluyen `Cache-Control: no-store` y `Pragma: no-cache`.

## Renovación y revocación

`POST /auth/refresh` recibe:

```json
{
  "refresh_token": "<último refresh token recibido>"
}
```

El refresh es un secreto aleatorio de 32 bytes. Su huella SHA-256 se guarda en SQLite. Conservar únicamente la huella reduce el impacto de una lectura de la tabla. No se necesita bcrypt para este secreto porque tiene alta entropía y no lo elige una persona.

Cada login crea una familia con un vencimiento absoluto de **siete días**, decisión de esta implementación. Renovar devuelve un nuevo access token y refresh token, consume el anterior y conserva el vencimiento de la familia.

Los permisos renovados son la intersección de los concedidos inicialmente con los actuales del usuario.

Un `UPDATE` condicional y una transacción hacen que dos peticiones concurrentes no puedan consumir válidamente el mismo refresh. Si se presenta uno ya consumido, se revoca toda su familia.

Los access tokens también consultan el estado de la familia, por lo que quedan invalidados inmediatamente cuando se revoca.

La pérdida de una respuesta de renovación obliga a iniciar sesión otra vez si se reintenta el refresh ya consumido. Es la política estricta de reutilización elegida para esta práctica.

## Roles y scopes

| Rol | Lectura | Escritura |
|---|---|---|
| `member` | Tareas, proyectos y categorías. | Tareas, proyectos y categorías. |
| `viewer` | Tareas, proyectos y categorías. | Denegada con 403. |

Los usuarios registrados anteriormente sin fila en `user_roles` se consideran `member` para conservar el comportamiento de la práctica anterior. Un rol desconocido recibe cero permisos.

Todos comparten el espacio de proyectos. Esta extensión introduce roles porque la rúbrica de excelente los pide. También protege las lecturas de negocio con su scope. Las rutas de sistema y las de registro y login permiten el acceso sin un JWT de acceso.

Para asignar el rol `viewer` a una cuenta existente, desde `taskflow-api`:

```cmd
python -m app.manage_users --username lector_prueba --role viewer
```

Para devolverle el rol `member`:

```cmd
python -m app.manage_users --username lector_prueba --role member
```

El registro público no permite autoasignarse un rol. Este comando requiere acceso local al equipo y a la base de datos.

Una reducción de rol se aplica a los JWT ya emitidos al consultar el rol actual. Un aumento de permisos requiere un nuevo login si el token previo carecía de esos scopes.

## Contrato de errores

| Estado | Causa |
|---|---|
| 401 + `WWW-Authenticate: Bearer` | Falta de token, firma inválida, caducidad o familia revocada. |
| 403 + información del scope | Identidad válida con permisos insuficientes. |
| 404 | Recurso CRUD inexistente tras superar la autorización. |
| 409 | Conflicto del CRUD, como una categoría con tareas. |
| 422 | Datos o parámetros inválidos. |

## Análisis de amenazas

| Amenaza | Medida aplicada | Límite que permanece |
|---|---|---|
| Lectura de contraseñas en la base de datos | Hash bcrypt con sal y coste 12. | Las contraseñas débiles pueden sufrir ataques offline. |
| Descubrimiento de usuarios por mensajes | Login y registro con respuestas genéricas. | El coste de las operaciones y factores externos pueden producir diferencias temporales. |
| Manipulación de un JWT | Firma HS256, algoritmo fijado y validación de claims. | El robo de la clave compromete las firmas. |
| Robo del access token | Duración de 30 minutos y familia verificable. | Un portador puede usarlo mientras siga vigente y autorizado. |
| Robo y reutilización del refresh | Secreto aleatorio, hash en base de datos, rotación y revocación de familia. | Un secreto robado puede usarse antes de que se detecte su reutilización. |
| Dos renovaciones simultáneas | Consumo mediante `UPDATE` condicional dentro de una transacción. | La sesión se revoca al detectar el segundo uso. |
| Solicitud de scopes superiores | Intersección con permisos del rol y rechazo de scopes no permitidos. | El operador local debe proteger su acceso a la base de datos. |
| Rol cambiado con un JWT antiguo | Comparación con el rol actual en cada petición. | Requiere consultar la base de datos. |
| Exposición de secretos en capturas o Git | Configuración por entorno y documentación sin tokens activos. | El operador debe revisar lo que publica. |
| Intercepción de credenciales | La demo se ejecuta en localhost. | Un despliegue por red requiere HTTPS. |

Esta práctica no incorpora un sistema de limitación de intentos de login. Se documenta la fuerza bruta como riesgo residual.

Los tokens se envían explícitamente como `Bearer` o en el cuerpo JSON. Un futuro cliente deberá evitar filtrarlos mediante XSS o almacenamiento accesible a scripts comprometidos.

## Endpoints principales

Las rutas de negocio requieren autenticación y el scope correspondiente.

| Recurso | Operaciones |
|---|---|
| `/auth/register` | POST: registro con mensaje genérico. |
| `/auth/login` | POST: formulario de login y emisión de tokens. |
| `/auth/refresh` | POST: renovación y rotación del refresh token. |
| `/tasks` | Crear y listar; obtener, sustituir y eliminar por ID. |
| `/projects` | Crear y listar; obtener, sustituir y eliminar por ID; resumen. |
| `/categories` | Crear y listar; obtener, sustituir y eliminar por ID; resumen. |
| Rutas de sistema | Comprobaciones de salud, versión y ping. |

## Pruebas y evidencias

Las imágenes corresponden a respuestas reales capturadas durante el desarrollo. Las primeras muestran el flujo anterior al cambio del contrato de registro; las demás corresponden a la actualización de seguridad. Las respuestas con tokens completos no se publican.

### Registro y acceso protegido

El registro inicial devolvió **201**. En la versión actual, el registro devuelve un mensaje genérico, como se muestra más adelante.

![Registro en la versión inicial](capturas/01_registro_inicial.png)

Una petición de escritura sin autenticar devolvió **401**.

![Petición sin autenticar](capturas/02_sin_token.png)

Una petición autenticada permitió crear una tarea y devolvió **201**.

![Tarea creada con autenticación](capturas/03_tarea_autorizada.png)

### Roles y scopes

Con el rol `viewer`, la lectura de proyectos devolvió **200** y la escritura devolvió **403**. Con `member`, la creación de un proyecto devolvió **201**.

![Viewer consulta proyectos](capturas/04_viewer_lectura.png)

![Viewer recibe 403 al escribir](capturas/05_viewer_escritura.png)

![Member crea un proyecto](capturas/06_member_escritura.png)

### Caducidad y cabecera de autenticación

La comprobación local obtuvo un token de la API, verificó su firma y comprobó la petición con el token vigente.

Después modificó el valor de expiración y firmó el nuevo token con la misma clave. El resultado fue **200** para el vigente y **401** con `WWW-Authenticate: Bearer` para el caducado.

La duración entre emisión y expiración del token original fue de **1800 segundos**.

![Prueba de caducidad](capturas/07_caducidad.png)

### Rotación y reutilización de refresh

En la prueba se renovó el refresh original, se reutilizó el anterior y después se presentó el nuevo de la misma familia. Las respuestas de los dos últimos pasos fueron **401**, coherentes con la revocación de la familia.

Estas capturas muestran las respuestas; los valores de los tokens no se publican.

![Respuesta tras reutilizar un refresh](capturas/08_refresh_reutilizado.png)

![Respuesta al usar el refresh de la familia revocada](capturas/09_familia_revocada.png)

### Registro genérico

Las dos peticiones de registro repetidas mostraron el mismo estado y mensaje, sin indicar al cliente si el nombre ya estaba registrado.

![Respuesta genérica de registro](capturas/10_registro_generico.png)

![Respuesta genérica al repetir el registro](capturas/11_registro_repetido.png)

### Sal y coste bcrypt

Se registraron dos cuentas de prueba con la misma contraseña. La consulta local comparó las sales sin mostrar los hashes completos: ambas tienen coste **12** y sus sales son diferentes.

![Comparación de sales y costes bcrypt](capturas/12_sal_coste.png)

