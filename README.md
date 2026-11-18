# Práctica 1.6 — CRUD completo con FastAPI y SQLAlchemy

## 1. Objetivo

En esta práctica se amplía la API de TaskFlow para implementar operaciones CRUD reales sobre los recursos:

- Tareas.
- Proyectos.
- Categorías.

Las operaciones utilizan SQLAlchemy y la base de datos SQLite configurada en la práctica anterior.

También se incorporan filtros, paginación y ordenación para las tareas, junto con contadores de proyectos y categorías.

---

## 2. Tecnologías utilizadas

| Tecnología | Uso en el proyecto |
|---|---|
| Python | Lenguaje de programación. |
| FastAPI | Creación de rutas y gestión de peticiones HTTP. |
| Pydantic | Validación de datos y definición de respuestas. |
| SQLAlchemy | Acceso a los datos mediante modelos ORM. |
| SQLite | Almacenamiento de la información. |
| Uvicorn | Servidor ASGI para ejecutar la aplicación. |
| Postman | Organización y prueba de las peticiones de la API. |

---

## 3. Estructura del proyecto

```text
taskflow-api/
├── app/
│   ├── __init__.py
│   ├── database.py
│   ├── main.py
│   ├── middleware.py
│   ├── models.py
│   ├── schemas.py
│   │
│   └── routers/
│       ├── __init__.py
│       ├── categories.py
│       ├── projects.py
│       ├── system.py
│       └── tasks.py
│
└── requirements.txt
```

### Responsabilidad de cada archivo

| Archivo | Responsabilidad |
|---|---|
| `database.py` | Configura el motor de SQLite y proporciona sesiones de base de datos. |
| `models.py` | Define las tablas y las relaciones mediante SQLAlchemy. |
| `schemas.py` | Define los datos de entrada y salida y sus validaciones. |
| `main.py` | Crea la aplicación y registra los routers y middleware. |
| `middleware.py` | Gestiona las cabeceras de tiempo e identificador y los errores inesperados. |
| `routers/tasks.py` | Gestiona el CRUD de tareas, los filtros y la paginación. |
| `routers/projects.py` | Gestiona el CRUD y el resumen de proyectos. |
| `routers/categories.py` | Gestiona el CRUD y el resumen de categorías. |
| `routers/system.py` | Agrupa los endpoints de estado y conectividad. |

---

## 4. Instalación y ejecución

Desde la carpeta `taskflow-api`, con el entorno virtual activado, instalar las dependencias:

```powershell
python -m pip install -r requirements.txt
```

Arrancar la aplicación:

```powershell
python -m uvicorn app.main:app --reload
```

Acceder a Swagger:

```text
http://127.0.0.1:8000/docs
```

La aplicación crea las tablas que falten al arrancar y utiliza el archivo SQLite `taskflow.db`.

---

## 5. Endpoints implementados

### 5.1. Tareas

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/tasks` | Lista tareas con filtros, paginación y ordenación. |
| GET | `/tasks/{task_id}` | Consulta una tarea por su ID. |
| POST | `/tasks` | Crea una tarea. |
| PUT | `/tasks/{task_id}` | Sustituye los campos editables de una tarea. |
| DELETE | `/tasks/{task_id}` | Elimina una tarea. |

### 5.2. Proyectos

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/projects` | Lista los proyectos. |
| GET | `/projects/{project_id}` | Consulta un proyecto e incluye sus tareas. |
| POST | `/projects` | Crea un proyecto. |
| PUT | `/projects/{project_id}` | Sustituye los campos editables de un proyecto. |
| DELETE | `/projects/{project_id}` | Elimina un proyecto y sus tareas asociadas. |
| GET | `/projects/summary` | Devuelve el total de proyectos y cuántos tienen tareas. |

### 5.3. Categorías

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/categories` | Lista las categorías. |
| GET | `/categories/{category_id}` | Consulta una categoría e incluye sus tareas. |
| POST | `/categories` | Crea una categoría. |
| PUT | `/categories/{category_id}` | Sustituye los campos editables de una categoría. |
| DELETE | `/categories/{category_id}` | Elimina una categoría si no tiene tareas asociadas. |
| GET | `/categories/summary` | Devuelve el total de categorías y cuántas tienen tareas. |

---

## 6. Filtros, paginación y ordenación de tareas

El endpoint `GET /tasks` admite los siguientes parámetros:

| Parámetro | Función | Valor por defecto |
|---|---|---|
| `project_id` | Filtra por proyecto. | Sin filtro. |
| `completed` | Filtra por estado `true` o `false`. | Sin filtro. |
| `skip` | Número de resultados que se omiten. | `0`. |
| `limit` | Número máximo de resultados. | `20`. |
| `sort_by` | Ordena por `id`, `title` o `created_at`. | `id`. |
| `order` | Dirección `asc` o `desc`. | `asc`. |

El límite debe estar entre `1` y `100`. Los filtros `project_id` y `completed` pueden combinarse.

Ejemplo:

```http
GET /tasks?project_id=3&completed=true&skip=0&limit=10&sort_by=title&order=asc
```

La respuesta incluye los resultados y los metadatos de paginación:

```json
{
  "items": [],
  "total": 0,
  "skip": 0,
  "limit": 10
}
```

`total` representa el número de tareas que cumplen los filtros antes de aplicar la paginación. Los valores anteriores son ilustrativos.

---

## 7. Relaciones y decisiones de borrado

Una tarea puede estar asociada opcionalmente a un proyecto y a una categoría.

### Proyectos

Cuando se elimina un proyecto, sus tareas asociadas se eliminan en cascada. La relación está configurada en SQLAlchemy y la clave foránea tiene `ON DELETE CASCADE`.

### Categorías

El endpoint de borrado devuelve **409 Conflict** si la categoría tiene tareas asociadas. Para eliminarla desde la API, primero hay que desvincularlas o asignarlas a otra categoría.

En la base de datos, la relación conserva `ON DELETE SET NULL` de la práctica 1.5. Por tanto, una eliminación directa de la categoría en SQLite desvincula las tareas. El bloqueo `409` es la política aplicada por el endpoint de la API.

Las claves foráneas se activan para cada conexión SQLite mediante `PRAGMA foreign_keys=ON`.

---

## 8. Optimización de consultas

- Los filtros y la paginación de tareas se aplican en la consulta SQL, por lo que solo se recupera la página solicitada.
- El número total de resultados se calcula con `COUNT`.
- Los resúmenes de proyectos y categorías calculan los contadores en la base de datos.
- Los detalles de proyectos y categorías utilizan `selectinload` para cargar sus tareas asociadas de forma explícita.

---

## 9. Manejo de errores y códigos HTTP

| Código | Uso en la API |
|---|---|
| `200 OK` | Consulta o modificación realizada correctamente. |
| `201 Created` | Recurso creado correctamente. |
| `204 No Content` | Recurso eliminado correctamente, sin cuerpo de respuesta. |
| `404 Not Found` | El recurso o una referencia indicada no existe. |
| `409 Conflict` | Se intenta borrar una categoría que tiene tareas. |
| `422 Unprocessable Entity` | Los datos o parámetros no cumplen el formato o las validaciones. |
| `500 Internal Server Error` | Se ha producido un error inesperado en el servidor. |

Los errores `404` diferencian si falta una tarea, un proyecto o una categoría. Los errores inesperados se registran en el servidor y devuelven al cliente un mensaje genérico.

---

## 10. Pruebas y evidencias

> Los ID de los ejemplos corresponden a los datos utilizados durante las pruebas.
> Si la base de datos devuelve otros ID, deben sustituirse por los reales.

### 10.1. Crear categoría

Ejecutar:

```http
POST /categories
```

Cuerpo:

```json
{
  "name": "Desarrollo",
  "color": "#2196F3"
}
```

**Resultado esperado:** `201 Created` y una categoría con su ID.

**Captura 1:** petición y respuesta de creación de categoría.

<!-- INSERTAR CAPTURA 1 AQUÍ -->

---

### 10.2. Crear proyecto

Ejecutar:

```http
POST /projects
```

Cuerpo:

```json
{
  "name": "Prueba CRUD 1.6",
  "description": "Proyecto para comprobar las operaciones CRUD"
}
```

**Resultado esperado:** `201 Created` y un proyecto con su ID.

**Captura 2:** petición y respuesta de creación de proyecto.

<!-- INSERTAR CAPTURA 2 AQUÍ -->

---

### 10.3. Crear tarea relacionada

Ejecutar:

```http
POST /tasks
```

Cuerpo:

```json
{
  "title": "Probar el CRUD",
  "description": "Tarea asociada al proyecto y a la categoría",
  "project_id": 3,
  "category_id": 1
}
```

**Resultado esperado:** `201 Created`, un ID para la tarea y las dos referencias enviadas.

**Captura 3:** creación de la tarea mostrando `project_id` y `category_id`.

<!-- INSERTAR CAPTURA 3 AQUÍ -->

---

### 10.4. Consultar los tres recursos

Ejecutar:

```http
GET /tasks/4
GET /projects/3
GET /categories/1
```

**Resultado esperado:** los tres devuelven `200 OK`. Los detalles del proyecto y de la categoría incluyen la tarea dentro de `tasks`.

**Captura 4:** detalle del proyecto con sus tareas.

<!-- INSERTAR CAPTURA 4 AQUÍ -->

**Captura 5:** detalle de la categoría con sus tareas.

<!-- INSERTAR CAPTURA 5 AQUÍ -->

---

### 10.5. Listar los tres recursos

Ejecutar:

```http
GET /tasks
GET /projects
GET /categories
```

**Resultado esperado:** los tres devuelven `200 OK`. El listado de tareas incluye `items`, `total`, `skip` y `limit`.

**Captura 6:** listado de tareas mostrando los metadatos.

<!-- INSERTAR CAPTURA 6 AQUÍ -->

---

### 10.6. Editar los tres recursos

#### Editar proyecto

```http
PUT /projects/3
```

```json
{
  "name": "Proyecto actualizado",
  "description": "Proyecto editado durante las pruebas"
}
```

#### Editar categoría

```http
PUT /categories/1
```

```json
{
  "name": "Desarrollo actualizado",
  "color": "#FF5733"
}
```

#### Editar tarea

```http
PUT /tasks/4
```

```json
{
  "title": "CRUD probado",
  "description": "Tarea editada durante las pruebas",
  "project_id": 3,
  "category_id": 1,
  "completed": true
}
```

**Resultado esperado:** los tres devuelven `200 OK` con los datos modificados.

**Captura 7:** respuesta del proyecto editado.

<!-- INSERTAR CAPTURA 7 AQUÍ -->

**Captura 8:** respuesta de la categoría editada.

<!-- INSERTAR CAPTURA 8 AQUÍ -->

**Captura 9:** respuesta de la tarea editada con `completed: true`.

<!-- INSERTAR CAPTURA 9 AQUÍ -->

---

### 10.7. Filtros y paginación

Después de marcar la tarea como completada, ejecutar:

```http
GET /tasks?project_id=3&completed=true&skip=0&limit=1
```

**Resultado esperado:** `200 OK`, la tarea aparece en `items` y la respuesta incluye `total`, `skip` y `limit`.

Para comprobar que se combinan los filtros, repetir con `completed=false`. La tarea completada no debe aparecer en esa respuesta.

Para comprobar la paginación con claridad, crear otra tarea en el mismo proyecto. Después consultar:

```http
GET /tasks?project_id=3&skip=0&limit=1
GET /tasks?project_id=3&skip=1&limit=1
```

**Resultado esperado:** cada página contiene como máximo un resultado y `total` refleja las tareas del proyecto que cumplen el filtro.

**Captura 10:** filtro por proyecto y estado.

<!-- INSERTAR CAPTURA 10 AQUÍ -->

**Capturas 11 y 12:** primera y segunda página, con los parámetros y la respuesta visibles.

<!-- INSERTAR CAPTURA 11 AQUÍ -->

<!-- INSERTAR CAPTURA 12 AQUÍ -->

---

### 10.8. Ordenación

Con varias tareas creadas, ejecutar:

```http
GET /tasks?sort_by=title&order=asc
```

Repetir con:

```http
GET /tasks?sort_by=title&order=desc
```

**Resultado esperado:** las tareas aparecen ordenadas por título en la dirección indicada.

**Capturas 13 y 14:** resultados con orden ascendente y descendente.

<!-- INSERTAR CAPTURA 13 AQUÍ -->

<!-- INSERTAR CAPTURA 14 AQUÍ -->

---

### 10.9. Resumen de proyectos y categorías

Ejecutar:

```http
GET /projects/summary
GET /categories/summary
```

**Resultado esperado:** `200 OK` y una respuesta con:

```json
{
  "total": 0,
  "with_tasks": 0
}
```

Los números anteriores son de ejemplo. Los valores reales dependen de los datos guardados.

**Capturas 15 y 16:** respuestas de ambos resúmenes.

<!-- INSERTAR CAPTURA 15 AQUÍ -->

<!-- INSERTAR CAPTURA 16 AQUÍ -->

---

### 10.10. Recursos inexistentes

Ejecutar con un ID que no exista:

```http
GET /tasks/999999
GET /projects/999999
GET /categories/999999
```

**Resultado esperado:** `404 Not Found` y un mensaje que identifica el recurso inexistente.

También se puede comprobar `PUT` y `DELETE` con un ID inexistente para cada recurso.

**Captura 17:** ejemplo de respuesta `404`.

<!-- INSERTAR CAPTURA 17 AQUÍ -->

---

### 10.11. Bloqueo al borrar una categoría con tareas

Mientras la categoría `1` tenga una tarea asociada, ejecutar:

```http
DELETE /categories/1
```

**Resultado esperado:** `409 Conflict` con el mensaje:

```json
{
  "detail": "La categoría tiene tareas asociadas"
}
```

**Captura 18:** petición y respuesta `409`.

<!-- INSERTAR CAPTURA 18 AQUÍ -->

---

### 10.12. Eliminar una tarea

Crear una tarea adicional para esta prueba y anotar su ID. Después ejecutar:

```http
DELETE /tasks/{id_de_la_tarea}
```

**Resultado esperado:** `204 No Content`.

Consultar después esa misma tarea mediante `GET /tasks/{id_de_la_tarea}`.

**Resultado esperado:** `404 Not Found`.

**Capturas 19 y 20:** borrado `204` y consulta posterior `404`.

<!-- INSERTAR CAPTURA 19 AQUÍ -->

<!-- INSERTAR CAPTURA 20 AQUÍ -->

---

### 10.13. Borrado de proyecto en cascada

Para esta prueba, crear un proyecto y una tarea asociados exclusivamente a él. Anotar ambos ID.

Ejecutar:

```http
DELETE /projects/{id_del_proyecto}
```

**Resultado esperado:** `204 No Content`.

Después consultar la tarea asociada:

```http
GET /tasks/{id_de_la_tarea}
```

**Resultado esperado:** `404 Not Found`, porque se ha eliminado junto al proyecto.

**Capturas 21 y 22:** borrado del proyecto y consulta posterior de la tarea.

<!-- INSERTAR CAPTURA 21 AQUÍ -->

<!-- INSERTAR CAPTURA 22 AQUÍ -->

---

### 10.14. Eliminar una categoría sin tareas

Crear una categoría sin tareas asociadas y anotar su ID. Después ejecutar:

```http
DELETE /categories/{id_de_la_categoria}
```

**Resultado esperado:** `204 No Content`.

Consultar después la misma categoría:

```http
GET /categories/{id_de_la_categoria}
```

**Resultado esperado:** `404 Not Found`.

**Capturas 23 y 24:** borrado de la categoría y consulta posterior.

<!-- INSERTAR CAPTURA 23 AQUÍ -->

<!-- INSERTAR CAPTURA 24 AQUÍ -->

---

## 11. Colección de Postman

La colección de Postman contiene las 15 peticiones CRUD indicadas en el enunciado:

- Cinco peticiones de tareas.
- Cinco peticiones de proyectos.
- Cinco peticiones de categorías.

También incluye las consultas de resumen para proyectos y categorías.

La colección debe ejecutarse con la API arrancada. Los identificadores utilizados en las peticiones deben corresponder a los registros existentes en la base de datos.

**Captura 25:** colección de Postman mostrando las carpetas y las peticiones.

<!-- INSERTAR CAPTURA 25 AQUÍ -->

**Captura 26:** resultado de la ejecución de la colección, si se ha ejecutado desde Postman.

<!-- INSERTAR CAPTURA 26 AQUÍ -->

---
