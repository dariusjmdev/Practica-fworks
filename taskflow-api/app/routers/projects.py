from datetime import datetime

from fastapi import APIRouter 

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
def create_project(project: ProjectCreate) -> ProjectRead:
    return ProjectRead(
        id=1,
        name=project.name,
        description=project.description,
        created_at=datetime.now()
    )