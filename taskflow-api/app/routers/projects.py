"""CRUD de proyectos, tareas asociadas y resumen agregado."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, Security
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.models import Project
from app.schemas import (
    ProjectCreate,
    ProjectDetail,
    ProjectRead,
    ResourceSummary,
)
from app.security import get_current_user


router = APIRouter(prefix="/projects", tags=["projects"])
DbSession = Annotated[Session, Depends(get_db)]


def get_project_or_404(project_id: int, db: Session) -> Project:
    """Busca un proyecto o devuelve un error 404."""
    record = db.get(Project, project_id)

    if record is None:
        raise HTTPException(
            status_code=404,
            detail="El proyecto no existe",
        )

    return record


# Las rutas fijas se declaran antes que las rutas con identificadores.
# Así FastAPI reconoce summary como una ruta y no intenta convertirlo a int.
@router.get(
    "/summary",
    response_model=ResourceSummary,
    summary="Resumen de proyectos",
    dependencies=[Security(get_current_user, scopes=["projects:read"])],
)
def project_summary(db: DbSession):
    # Los contadores se calculan en SQLite sin cargar todos los proyectos.
    return {
        "total": db.scalar(select(func.count(Project.id))),
        "with_tasks": db.scalar(
            select(func.count(Project.id)).where(Project.tasks.any())
        ),
    }


@router.get(
    "",
    response_model=list[ProjectRead],
    summary="Listar proyectos",
    dependencies=[Security(get_current_user, scopes=["projects:read"])],
)
def list_projects(db: DbSession):
    return db.scalars(
        select(Project).order_by(Project.id)
    ).all()


@router.get(
    "/{project_id}",
    response_model=ProjectDetail,
    summary="Consultar proyecto",
    dependencies=[Security(get_current_user, scopes=["projects:read"])],
)
def read_project(project_id: int, db: DbSession):
    # selectinload carga las tareas asociadas de forma explícita.
    # Evita consultar por separado cada tarea durante la serialización.
    query = (
        select(Project)
        .options(selectinload(Project.tasks))
        .where(Project.id == project_id)
    )

    record = db.scalar(query)

    if record is None:
        raise HTTPException(
            status_code=404,
            detail="El proyecto no existe",
        )

    return record


@router.post(
    "",
    response_model=ProjectRead,
    status_code=201,
    summary="Crear proyecto",
    dependencies=[Security(get_current_user, scopes=["projects:write"])],
)
def create_project(project: ProjectCreate, db: DbSession):
    record = Project(**project.model_dump())

    db.add(record)
    db.commit()

    return record


@router.put(
    "/{project_id}",
    response_model=ProjectRead,
    summary="Editar proyecto",
    dependencies=[Security(get_current_user, scopes=["projects:write"])],
)
def update_project(
    project_id: int,
    project: ProjectCreate,
    db: DbSession,
):
    record = get_project_or_404(project_id, db)

    # Sustituimos los campos editables y confirmamos la modificación.
    record.name = project.name
    record.description = project.description

    db.commit()

    return record


@router.delete(
    "/{project_id}",
    status_code=204,
    summary="Eliminar proyecto",
    dependencies=[Security(get_current_user, scopes=["projects:write"])],
)
def delete_project(project_id: int, db: DbSession):
    record = get_project_or_404(project_id, db)

    # El modelo y ON DELETE CASCADE gestionan sus tareas asociadas.
    db.delete(record)
    db.commit()

    return Response(status_code=204)