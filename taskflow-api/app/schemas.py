from datetime import datetime 

from pydantic import BaseModel, Field

class TaskCreate(BaseModel):
    """Schema para crear tareas."""
    title: str = Field(
        min_length=1,
        max_length=100
    )

    description: str | None = None
    project_id: int | None = None
    category_id: int | None = None

class TaskRead(TaskCreate):
    """Schema para leer tareas."""
    id: int
    completed: bool
    created_at: datetime
    
class ProjectCreate(BaseModel):
    """Schema para crear proyectos."""
    name: str = Field(min_length=1)
    description: str | None = None

class ProjectRead(ProjectCreate): 
    """Schema para leer proyectos."""
    id: int
    created_at: datetime