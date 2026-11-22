from fastapi import APIRouter, HTTPException, Query, status

from app.api.deps import CurrentUser, DbSession
from app.schemas.task import TaskCreate, TaskResponse, TaskUpdate
from app.services.task import (
    create_task,
    delete_task,
    get_task_by_id,
    get_tasks_by_owner,
    update_task,
)

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.get("", response_model=list[TaskResponse])
async def list_tasks(
    db: DbSession,
    current_user: CurrentUser,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
) -> list[TaskResponse]:
    tasks = await get_tasks_by_owner(db, current_user.id, skip=skip, limit=limit)
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


@router.put("/{task_id}", response_model=TaskResponse)
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
