# Práctica 1.4 — Middleware

## Objetivo

En esta práctica se amplía la API de TaskFlow para añadir funcionalidades que se aplican de forma común a las peticiones y respuestas:

- Configuración de CORS para permitir el acceso desde el frontend.
- Medición del tiempo de procesamiento de cada petición.
- Identificación de las peticiones mediante un `request_id`.
- Gestión global de errores inesperados.

Además, se han trasladado los endpoints `/health`, `/version` y `/ping` a un router propio, siguiendo la indicación recibida en la práctica anterior.

---

## Estructura del proyecto

```text
taskflow-api/
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── middleware.py
│   ├── schemas.py
│   │
│   └── routers/
│       ├── __init__.py
│       ├── system.py
│       ├── tasks.py
│       └── projects.py
│
└── requirements.txt

README.md
```

### Responsabilidad de cada archivo

| Archivo | Responsabilidad |
|---|---|
| `main.py` | Crea la aplicación, configura los middleware y registra los routers. |
| `middleware.py` | Contiene la medición del tiempo, la identificación de las peticiones y la gestión de errores inesperados. |
| `routers/system.py` | Agrupa los endpoints `/health`, `/version` y `/ping`. |
| `routers/tasks.py` | Agrupa los endpoints relacionados con las tareas. |
| `routers/projects.py` | Agrupa los endpoints relacionados con los proyectos. |
| `schemas.py` | Define los modelos de entrada y salida de tareas y proyectos. |

---

## ¿Qué es un middleware?

Un middleware es una capa que interviene en el recorrido de una petición HTTP. Puede ejecutar acciones antes de que la petición llegue al endpoint y también modificar o completar la respuesta antes de que llegue al cliente.

Permite aplicar un comportamiento común a varias rutas sin tener que repetirlo en cada endpoint.

En esta práctica se utiliza para configurar CORS, medir el tiempo, identificar las peticiones y gestionar errores inesperados.

---

## Configuración de CORS

Se ha configurado `CORSMiddleware` para permitir por defecto las peticiones desde:

```text
http://localhost:5173
```

Este es el origen del frontend indicado en el enunciado.

La configuración permite los métodos `GET`, `POST` y `OPTIONS`, y las cabeceras de petición `Content-Type` y `Authorization`.

Los orígenes se pueden configurar mediante la variable de entorno `ALLOWED_ORIGINS`. Para indicar varios orígenes, se separan mediante comas.

Ejemplo en PowerShell:

```powershell
$env:ALLOWED_ORIGINS = "http://localhost:5173,https://frontend.ejemplo.com"
uvicorn app.main:app --reload
```

El dominio `frontend.ejemplo.com` es únicamente ilustrativo; debe sustituirse por el origen real si se necesita.

También se ha configurado:

```python
expose_headers=["X-Process-Time", "X-Request-ID"]
```

Esto permite que un frontend autorizado pueda leer esas cabeceras desde JavaScript en peticiones entre distintos orígenes.

> CORS es una política aplicada por los navegadores. Herramientas como Postman o `curl` pueden enviar peticiones aunque el origen no esté autorizado.

---

## Medición del tiempo de procesamiento

El middleware `RequestContextMiddleware` utiliza `perf_counter()` para medir el tiempo transcurrido durante el procesamiento de la petición.

El resultado se añade a la respuesta mediante la cabecera:

```text
X-Process-Time: 5.40 ms
```

El valor se expresa en milisegundos y cambia en cada petición.

Esta medición llega hasta que la aplicación comienza a devolver la respuesta. En respuestas de tipo streaming, no mide necesariamente el tiempo de envío completo.

---

## Identificador de petición

Cada petición recibe un identificador generado con `uuid4()`. Se devuelve en la cabecera:

```text
X-Request-ID: identificador-unico
```

El identificador también se guarda en el estado de la petición. Si ocurre un error, se incluye en el registro del servidor para facilitar la relación entre la respuesta recibida y el error registrado.

---

## Gestión de errores inesperados

Se ha registrado un manejador global de excepciones. Además, `ErrorHandlingMiddleware` captura los errores inesperados de las capas interiores y utiliza ese mismo manejador para generar la respuesta.

Cuando ocurre un error no controlado:

1. Se registra el error con sus detalles en el servidor.
2. Se devuelve al cliente el estado `500 Internal Server Error`.
3. Se muestra un mensaje genérico sin exponer el stacktrace.
4. Se añade un `error_code` para identificar el tipo de error.

Ejemplo de respuesta:

```json
{
  "error": "Se ha producido un error interno en el servidor.",
  "error_code": "INTERNAL_SERVER_ERROR"
}
```

Los detalles de la excepción se mantienen en los registros del servidor para poder investigar el problema.

---

## Orden de ejecución

Los middleware se añaden en `main.py` teniendo en cuenta que la última capa registrada es la primera que recibe la petición.

El recorrido de una petición es:

1. **`RequestContextMiddleware`**: inicia la medición y genera el identificador.
2. **`CORSMiddleware`**: comprueba el origen y aplica las cabeceras CORS correspondientes.
3. **`ErrorHandlingMiddleware`**: captura errores inesperados de las capas interiores.
4. **Endpoint**: procesa la petición.

La respuesta vuelve atravesando las capas en sentido inverso.

Si un endpoint produce un error, `ErrorHandlingMiddleware` llama al manejador, que registra la excepción y genera la respuesta 500. Después, las capas exteriores pueden añadir sus cabeceras a esa respuesta.

---

## Pruebas realizadas

### 1. Comprobación de rutas y cabeceras

Se ha ejecutado `GET /ping` desde Swagger.

**Resultado obtenido:**

- Estado `200 OK`.
- Respuesta `{"message": "pong"}`.
- Cabecera `X-Process-Time`.
- Cabecera `X-Request-ID`.

<img width="1300" height="270" alt="image" src="https://github.com/user-attachments/assets/32013598-92c0-4e58-9b20-029b574111af" />


---

### 2. CORS con origen permitido

Se ha realizado una petición preflight con el origen permitido:

```powershell
curl.exe -i -X OPTIONS http://127.0.0.1:8000/ping -H "Origin: http://localhost:5173" -H "Access-Control-Request-Method: GET"
```

**Resultado obtenido:**

- Estado `200 OK`.
- Cabecera `access-control-allow-origin: http://localhost:5173`.
- Presencia de `X-Process-Time` y `X-Request-ID`.

<img width="1387" height="323" alt="image" src="https://github.com/user-attachments/assets/df5a9c1e-57ac-4e0f-820c-2b52936db632" />


---

### 3. CORS con origen no permitido

Se ha repetido la petición con un origen no autorizado:

```powershell
curl.exe -i -X OPTIONS http://127.0.0.1:8000/ping -H "Origin: http://ejemplo-no-permitido.com" -H "Access-Control-Request-Method: GET"
```

**Resultado obtenido:**

- Estado `400 Bad Request`.
- Mensaje `Disallowed CORS origin`.
- El origen no aparece autorizado en `access-control-allow-origin`.
- Las cabeceras de tiempo e identificador siguen presentes.

<img width="1391" height="295" alt="image" src="https://github.com/user-attachments/assets/3d90b277-d068-4d4e-8fc4-5cb6c8fa16d2" />


---

### 4. Error inesperado

Para comprobar el manejo de excepciones, se ha creado temporalmente una ruta que provoca un error:

```python
@router.get("/test-error", include_in_schema=False)
def test_error():
    raise RuntimeError("Error interno de prueba")
```

Se ha realizado la siguiente petición:

```powershell
curl.exe -i http://127.0.0.1:8000/test-error
```

**Resultado obtenido:**

- Estado `500 Internal Server Error`.
- Respuesta JSON con mensaje genérico y `error_code`.
- El stacktrace no aparece en la respuesta del cliente.
- Se incluyen `X-Process-Time` y `X-Request-ID`.

<img width="1178" height="232" alt="image" src="https://github.com/user-attachments/assets/cf0dde1e-1315-4793-abd5-c00599b6fc57" />


---
