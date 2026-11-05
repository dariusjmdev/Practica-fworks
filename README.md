# Práctica 1.3 - Organización con APIRouter

## Objetivo

Reorganizar la aplicación FastAPI utilizando `APIRouter` para separar los endpoints por recursos y mejorar la mantenibilidad del proyecto.

La práctica tiene como finalidad eliminar la lógica de negocio de `main.py` y distribuir las rutas en módulos independientes, agrupados según el recurso al que pertenecen.

---

# Arquitectura del proyecto

```text
app/
├── __init__.py
├── main.py
├── schemas.py
│
└── routers/
    ├── __init__.py
    ├── tasks.py
    └── projects.py
```

## Descripción de cada componente

### main.py

Punto de entrada de la aplicación.

Responsabilidades:

- Crear la instancia de FastAPI.
- Configurar metadatos de la API.
- Registrar los routers mediante `include_router()`.

No contiene lógica de negocio ni implementación de endpoints.

---

### schemas.py

Contiene los modelos Pydantic utilizados como contrato de entrada y salida de la API.

Schemas implementados:

- TaskCreate
- TaskRead
- ProjectCreate
- ProjectRead

Además, mantiene la validación definida en la práctica anterior:

```python
Field(min_length=1, max_length=100)
```

para el campo `title`.

---

### routers/tasks.py

Contiene todos los endpoints relacionados con tareas.

Configuración:

```python
APIRouter(
    prefix="/tasks",
    tags=["tasks"]
)
```

Endpoint implementado:

```http
POST /tasks
```

---

### routers/projects.py

Contiene todos los endpoints relacionados con proyectos.

Configuración:

```python
APIRouter(
    prefix="/projects",
    tags=["projects"]
)
```

Endpoint implementado:

```http
POST /projects
```

---

# Beneficios de utilizar APIRouter

La división por routers aporta varias ventajas:

- Separación clara de responsabilidades.
- Mayor facilidad de mantenimiento.
- Mejor escalabilidad para futuras funcionalidades.
- Código más legible y organizado.
- Posibilidad de trabajar en distintos recursos de forma independiente.

Sin esta organización, todos los endpoints crecerían dentro de un único archivo (`main.py`), generando un diseño monolítico difícil de mantener.

---

# Registro de routers

Los routers se registran desde `main.py`:

```python
app.include_router(tasks_router)
app.include_router(projects_router)
```

De esta forma FastAPI incorpora automáticamente todas las rutas al iniciar la aplicación.

---

# Convención REST utilizada

Se ha adoptado una nomenclatura basada en recursos utilizando nombres en plural.

| Recurso | URL |
|----------|----------|
| Tasks | `/tasks` |
| Projects | `/projects` |

Esta convención mejora la consistencia y la claridad de la API.

---

# Pruebas realizadas

## Creación de tarea válida

Petición:

```json
{
  "title": "Mi primera tarea",
  "description": "Descripción de prueba",
  "project_id": 1
}
```

Resultado esperado:

```http
201 Created
```

---

## Validación de título vacío

Petición:

```json
{
  "title": "",
  "description": "Descripción de prueba",
  "project_id": 1
}
```

Resultado esperado:

```http
422 Unprocessable Entity
```

Se verifica que continúa funcionando la validación implementada en la práctica 1.2.

---

## Creación de proyecto válida

Petición:

```json
{
  "name": "Proyecto API",
  "description": "Proyecto de prueba"
}
```

Resultado esperado:

```http
201 Created
```

---

# Evidencias (capturas)

## Captura 1 - Estructura del proyecto

"Captura 1 (la añadire en el commit 2)"

---

## Captura 2 - Swagger agrupado por tags

"Captura 2 (la añadire en el commit 2)"

---

## Captura 3 - Endpoint POST /tasks

"Captura 3 (la añadire en el commit 2)"

---

## Captura 4 - Endpoint POST /projects

"Captura 4 (la añadire en el commit 2)"
---

## Captura 5 - Creación de tarea válida

"Captura 5 (la añadire en el commit 2)"

---

## Captura 6 - Error de validación

"Captura 6 (la añadire en el commit 2)"

---
