from typing import Annotated


from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Project 


from app.schemas import ProjectCreate, ProjectRead

router = APIRouter(
    prefix="/projects",
    tags=["projects"]
)

@router.post(
    "",
    response_model=ProjectRead,
    status_code=201,
    summary="Crear proyecto"
)
def create_project(
    project: ProjectCreate,
    db: Annotated[Session, Depends(get_db)]
) -> ProjectRead:
    # project contiene el JSON validado. db es la sesión de esta petición.
    # Construimos la entidad de SQLAlchemy con los datos recibidos.
    record = Project(name=project.name, description=project.description)
    db.add(record)
    db.commit() 
    return ProjectRead.model_validate(
        record,
        from_attributes=True
    )