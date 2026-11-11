# Práctica 1.5 — Modelos SQLAlchemy y conexión a base de datos

## Objetivo

En esta práctica se incorpora persistencia a TaskFlow mediante **SQLAlchemy y SQLite**. Los proyectos y las tareas creados mediante la API se guardan en la base de datos `taskflow.db`.

También se definen los modelos `User`, `Project`, `Category` y `Task`, sus relaciones y una dependencia de FastAPI que proporciona una sesión de base de datos a cada petición.

---

## Estructura del proyecto

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
│       ├── projects.py
│       ├── system.py
│       └── tasks.py
│
└── requirements.txt
```

| Archivo | Responsabilidad |
|---|---|
| `database.py` | Configura el motor SQLite, la fábrica de sesiones y la dependencia `get_db()`. |
| `models.py` | Define las tablas y sus relaciones mediante SQLAlchemy. |
| `schemas.py` | Define y valida los datos de entrada y salida de la API. |
| `main.py` | Configura la aplicación, los middleware, los routers y la creación inicial de tablas. |
| `routers/projects.py` | Contiene la creación de proyectos. |
| `routers/tasks.py` | Contiene la creación de tareas y la comprobación de sus referencias. |
| `routers/system.py` | Agrupa `/health`, `/version` y `/ping`. |

---

## SQLAlchemy y el ORM

Un ORM permite trabajar con tablas de una base de datos mediante clases y objetos de Python.

En TaskFlow, cada modelo representa una tabla. Por ejemplo:

- La clase `Project` representa la tabla `projects`.
- Un objeto `Project` representa un proyecto que puede guardarse como una fila.
- Los atributos de la clase corresponden a las columnas de la tabla.

El ORM resulta útil para crear objetos, consultar datos y recorrer relaciones desde Python. SQL directo puede ser apropiado cuando se necesita controlar una consulta con precisión, por ejemplo, para realizar agregaciones o analizar su rendimiento.

---

## Modelo de datos

```mermaid
erDiagram
    PROJECT o|--o{ TASK : agrupa
    CATEGORY o|--o{ TASK : clasifica

    USER {
        int id PK
        string username UK
        string hashed_password
    }

    PROJECT {
        int id PK
        string name
        string description "Opcional"
        datetime created_at
    }

    CATEGORY {
        int id PK
        string name
        string color
    }

    TASK {
        int id PK
        string title "Máximo 100 caracteres"
        string description "Opcional"
        boolean completed
        datetime created_at
        int project_id FK "Opcional"
        int category_id FK "Opcional"
    }
```

### Decisiones del modelo

- Los usuarios trabajan en un **espacio compartido**, tal y como se indica para esta práctica. Por ello, `Project` no tiene `owner_id`.
- Una tarea puede existir sin proyecto y sin categoría.
- Un proyecto puede tener varias tareas y una categoría puede clasificar varias tareas.
- `back_populates` conecta los dos lados de cada relación. Por ejemplo, permite consultar `project.tasks` y `task.project`.
- Al eliminar un proyecto, sus tareas asociadas se eliminan en cascada.
- Al eliminar una categoría, sus tareas se conservan y su `category_id` pasa a `NULL`.
- `Project.created_at` conserva la información que ya devolvía el endpoint de proyectos en la práctica anterior.

---

## Conexión a SQLite

El archivo `app/database.py` configura el motor de SQLAlchemy y, por defecto, utiliza:

```text
taskflow-api/taskflow.db
```

La ruta puede cambiarse mediante la variable de entorno `TASKFLOW_DB_PATH`.

La conexión utiliza `check_same_thread=False` para permitir que las distintas partes síncronas de una petición de FastAPI puedan ejecutarse en hilos diferentes. Cada petición utiliza su propia sesión.

También se activa `PRAGMA foreign_keys=ON` en cada conexión. Esto permite que SQLite compruebe las claves foráneas y aplique las reglas de borrado configuradas.

### Configuración por entorno

| Variable | Valor por defecto | Función |
|---|---:|---|
| `TASKFLOW_DB_PATH` | Ruta de `taskflow-api/taskflow.db` | Permite usar otro archivo de base de datos. |
| `TASKFLOW_SQLITE_TIMEOUT` | 5 segundos | Tiempo de espera ante un bloqueo de SQLite. |
| `TASKFLOW_POOL_TIMEOUT` | 10 segundos | Tiempo máximo de espera por una conexión disponible del pool. |

SQLAlchemy reutiliza conexiones mediante un pool. La opción `pool_pre_ping=True` comprueba una conexión cuando se obtiene del pool para usarla.

---

## Ciclo de vida de la sesión

`SessionLocal` es la fábrica que crea las sesiones de SQLAlchemy.

La dependencia `get_db()`:

1. Crea una sesión.
2. La proporciona a la petición mediante `yield`.
3. La cierra en `finally`, aunque durante la petición se produzca una excepción.

La opción `expire_on_commit=False` mantiene disponibles los atributos cargados de los objetos después de confirmar los cambios con `commit()`.

### Dependencias anidadas

En `POST /tasks`, la función `validate_task_references()` recibe la sesión mediante `Depends(get_db)` y comprueba que el proyecto y la categoría existan cuando se indican.

La ruta también recibe `Depends(get_db)`. FastAPI reutiliza la sesión dentro de la misma petición, de modo que la comprobación y la inserción trabajan con ella.

Las rutas de sistema declaran la dependencia a nivel de router. Estas rutas devuelven información fija y no necesitan ejecutar consultas.

---

## Pruebas realizadas

### 1. Creación de un proyecto

En Swagger, ejecutar `POST /projects` con:

```json
{
  "name": "Proyecto de prueba"
}
```

**Resultado esperado:** `201 Created`, con un identificador generado, la descripción y la fecha de creación.

<img width="1300" height="315" alt="image" src="https://github.com/user-attachments/assets/2f73e5ca-fb92-41b9-8215-66d924931818" />


---

### 2. Creación de una tarea asociada a un proyecto

Ejecutar `POST /tasks` con el identificador obtenido en la prueba anterior. El siguiente `1` es un ejemplo y debe sustituirse por el ID real:

```json
{
  "title": "Preparar la entrega",
  "project_id": 1
}
```

**Resultado esperado:** `201 Created`, con el `project_id` indicado y `completed: false`.

<img width="1303" height="317" alt="image" src="https://github.com/user-attachments/assets/d45f1101-cb46-4dd3-8a9d-2a4e049e66b7" />


---

### 3. Referencias inexistentes

Para comprobar un proyecto inexistente, ejecutar `POST /tasks` con un ID positivo que no exista:

```json
{
  "title": "Proyecto inexistente",
  "project_id": 999999
}
```

**Resultado esperado:** `404` con `El proyecto no existe`.

Para comprobar una categoría inexistente, ejecutar por separado:

```json
{
  "title": "Categoría inexistente",
  "category_id": 999999
}
```

**Resultado esperado:** `404` con `La categoría no existe`.

<img width="1302" height="308" alt="image" src="https://github.com/user-attachments/assets/1e8808c2-1f35-4afa-be84-2ebf951f9edf" />

<img width="1307" height="307" alt="image" src="https://github.com/user-attachments/assets/3d05a25c-525e-4310-8e79-c27c7d0425f0" />

<!-- INSERTAR AQUÍ LA CAPTURA 4: CATEGORÍA INEXISTENTE -->

---

### 4. Validación del título

Ejecutar `POST /tasks` con:

```json
{
  "title": ""
}
```

**Resultado esperado:** `422 Unprocessable Entity`, porque el título no puede estar vacío.

<img width="1298" height="305" alt="image" src="https://github.com/user-attachments/assets/e69edc08-d7c2-4fda-8940-984b61876545" />


---

### 5. Tarea sin proyecto ni categoría

Ejecutar `POST /tasks` con:

```json
{
  "title": "Tarea independiente"
}
```

**Resultado esperado:** `201 Created`, con `project_id: null` y `category_id: null`.

<img width="1311" height="316" alt="image" src="https://github.com/user-attachments/assets/0abf3f24-fc76-4810-9b97-bfc038b0e435" />


---

### 6. Persistencia después de reiniciar

1. Detener Uvicorn con `Ctrl+C`.
2. Volver a arrancarlo.
3. Abrir otra terminal en `taskflow-api` y ejecutar:

```powershell
python -c "import sqlite3; db = sqlite3.connect('file:taskflow.db?mode=ro', uri=True); print('Proyectos:', db.execute('SELECT id, name FROM projects').fetchall()); print('Tareas:', db.execute('SELECT id, title, project_id, category_id FROM tasks').fetchall()); db.close()"
```

**Resultado esperado:** los proyectos y las tareas válidas siguen en la base de datos después del reinicio. La tarea asociada conserva el identificador de su proyecto.

<img width="1892" height="113" alt="image" src="https://github.com/user-attachments/assets/eeb58778-cf91-40b2-92e1-b1fa67822fd1" />

---
