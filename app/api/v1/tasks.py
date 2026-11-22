from typing import Literal

from fastapi import APIRouter, HTTPException, Query, status

from app.api.deps import CurrentUser, DbSession
from app.models.task import TaskPriority, TaskStatus
from app.schemas.task import TaskCreate, TaskResponse, TaskUpdate
from app.services.task import (
    create_task,
    delete_task,
    get_task_by_id,
    get_tasks_by_owner,
    update_task,
)

router = APIRouter(prefix="/tasks", tags=["Tasks"])


@router.get("", response_model=list[TaskResponse], summary="List tasks")
async def list_tasks(
    db: DbSession,
    current_user: CurrentUser,
    skip: int = Query(0, ge=0, description="Number of tasks to skip"),
    limit: int = Query(100, ge=1, le=100, description="Maximum tasks to return"),
    status: TaskStatus | None = Query(None, description="Filter by status"),
    priority: TaskPriority | None = Query(None, description="Filter by priority"),
    sort_by: Literal["created_at", "due_date"] = Query(
        "created_at", description="Field to sort by"
    ),
    sort_order: Literal["asc", "desc"] = Query("desc", description="Sort direction"),
) -> list[TaskResponse]:
    """List all tasks for the current user with optional filters and sorting."""
    tasks = await get_tasks_by_owner(
        db,
        current_user.id,
        skip=skip,
        limit=limit,
        status=status,
        priority=priority,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    return [TaskResponse.model_validate(t) for t in tasks]


@router.post("", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_new_task(
    db: DbSession,
    current_user: CurrentUser,
    task_in: TaskCreate,
) -> TaskResponse:
    task = await create_task(db, task_in, current_user.id)
    return TaskResponse.model_validate(task)


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(
    db: DbSession,
    current_user: CurrentUser,
    task_id: int,
) -> TaskResponse:
    task = await get_task_by_id(db, task_id)
    if not task or task.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )
    return TaskResponse.model_validate(task)


@router.patch("/{task_id}", response_model=TaskResponse, summary="Update a task")
async def update_existing_task(
    db: DbSession,
    current_user: CurrentUser,
    task_id: int,
    task_in: TaskUpdate,
) -> TaskResponse:
    task = await get_task_by_id(db, task_id)
    if not task or task.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )
    task = await update_task(db, task, task_in)
    return TaskResponse.model_validate(task)


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_existing_task(
    db: DbSession,
    current_user: CurrentUser,
    task_id: int,
) -> None:
    task = await get_task_by_id(db, task_id)
    if not task or task.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )
    await delete_task(db, task)
