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
  "name": "Desarrollo2",
  "color": "#2196F3"
}
```

**Resultado esperado:** `201 Created` y una categoría con su ID.

<img width="860" height="121" alt="image" src="https://github.com/user-attachments/assets/da38dae8-ecb8-4cc9-8c0f-4d89008a9cc6" />


---

### 10.2. Crear proyecto

Ejecutar:

```http
POST /projects
```

Cuerpo:

```json
{
  "name": "Prueba 2 CRUD 1.6",
  "description": "Proyecto para comprobar las operaciones CRUD"
}
```

**Resultado esperado:** `201 Created` y un proyecto con su ID.

<img width="867" height="125" alt="image" src="https://github.com/user-attachments/assets/41efffad-82af-4349-8bbb-f892c48a4ecb" />


---

### 10.3. Crear tarea relacionada

Ejecutar:

```http
POST /tasks
```

Cuerpo:

```json
{
  "title": "Probar el CRUD 2",
  "description": "Tarea asociada al proyecto y a la categoría",
  "project_id": 4,
  "category_id": 2
}
```

**Resultado esperado:** `201 Created`, un ID para la tarea y las dos referencias enviadas.

<img width="868" height="160" alt="image" src="https://github.com/user-attachments/assets/449e611d-0509-46ae-ba1c-60dda9d2abda" />


---

### 10.4. Consultar los tres recursos

Ejecutar:

```http
GET /tasks/5
GET /projects/4
GET /categories/2
```

**Resultado esperado:** los tres devuelven `200 OK`. Los detalles del proyecto y de la categoría incluyen la tarea dentro de `tasks`.

<img width="865" height="160" alt="image" src="https://github.com/user-attachments/assets/433c7ef9-9bb6-4050-8b6b-9c11a5b6a7a4" />


<img width="860" height="275" alt="image" src="https://github.com/user-attachments/assets/3f6c2096-2df7-448c-8e7e-b036180d2929" />


---

### 10.5. Listar los tres recursos

Ejecutar:

```http
GET /tasks
GET /projects
GET /categories
```

**Resultado esperado:** los tres devuelven `200 OK`. El listado de tareas incluye `items`, `total`, `skip` y `limit`.

<img width="866" height="413" alt="image" src="https://github.com/user-attachments/assets/98075e89-00ff-4806-91c2-31fd0fef238f" />

---

### 10.6. Editar los tres recursos

#### Editar proyecto

```http
PUT /projects/4
```

```json
{
  "name": "Proyecto actualizado",
  "description": "Proyecto editado durante las pruebas"
}
```

#### Editar categoría

```http
PUT /categories/2
```

```json
{
  "name": "Desarrollo actualizado",
  "color": "#FF5733"
}
```

#### Editar tarea

```http
PUT /tasks/5
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

<img width="861" height="135" alt="image" src="https://github.com/user-attachments/assets/c8f0d23a-73b1-4892-98a7-b13f6c85f88d" />


<img width="862" height="263" alt="image" src="https://github.com/user-attachments/assets/3acc96f4-1b80-41b0-8ead-67b9f65a4e29" />


**Captura 9:** respuesta de la tarea editada con `completed: true`.

<img width="867" height="161" alt="image" src="https://github.com/user-attachments/assets/8f31bea8-5b19-4e6f-a84d-3de0068d942c" />


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

<img width="866" height="255" alt="image" src="https://github.com/user-attachments/assets/7cb64937-35df-43cc-a0ea-6926eb63a39f" />


<img width="862" height="250" alt="image" src="https://github.com/user-attachments/assets/0c3e94c4-98b6-4df4-b931-f72fc72fd51e" />


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

<img width="867" height="416" alt="image" src="https://github.com/user-attachments/assets/b6700d91-8a20-487f-94a0-899ee246489c" />


<img width="860" height="416" alt="image" src="https://github.com/user-attachments/assets/c93c9e9b-e20e-436b-bd2f-f3d943e354dd" />


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

<img width="861" height="97" alt="image" src="https://github.com/user-attachments/assets/6769895e-a600-4160-a8bc-1a80a23b077a" />


<img width="865" height="101" alt="image" src="https://github.com/user-attachments/assets/6ba52154-f6ef-4562-a0aa-61c152fefe0e" />


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

<img width="870" height="127" alt="image" src="https://github.com/user-attachments/assets/d0bf5b3c-62a4-407b-8e3f-13425e7befca" />


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

<img width="858" height="115" alt="image" src="https://github.com/user-attachments/assets/5bd0bd94-8251-46a4-8735-7e33bc144d6d" />


---

### 10.12. Eliminar una tarea

Crear una tarea adicional para esta prueba y anotar su ID. Después ejecutar:

```http
DELETE /tasks/{id_de_la_tarea}
```

**Resultado esperado:** `204 No Content`.

Consultar después esa misma tarea mediante `GET /tasks/{id_de_la_tarea}`.

**Resultado esperado:** `404 Not Found`.

<img width="241" height="75" alt="image" src="https://github.com/user-attachments/assets/94448098-6387-4be0-b4c4-ce95aa258b9c" />


<img width="322" height="128" alt="image" src="https://github.com/user-attachments/assets/1d8cab8b-288f-4d19-aa57-6774a2f978fa" />


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

<img width="241" height="75" alt="image" src="https://github.com/user-attachments/assets/94448098-6387-4be0-b4c4-ce95aa258b9c" />

<img width="313" height="122" alt="image" src="https://github.com/user-attachments/assets/b0948415-2775-42f6-9362-48324dfa5319" />


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

<img width="241" height="75" alt="image" src="https://github.com/user-attachments/assets/94448098-6387-4be0-b4c4-ce95aa258b9c" />

<img width="328" height="113" alt="image" src="https://github.com/user-attachments/assets/bf0bd198-dddb-42f0-ab9f-36fd6344be29" />

---
