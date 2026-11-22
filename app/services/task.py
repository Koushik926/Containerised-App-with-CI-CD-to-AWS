from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Task
from app.schemas.task import TaskCreate, TaskUpdate


async def get_task_by_id(db: AsyncSession, task_id: int) -> Task | None:
    result = await db.execute(select(Task).where(Task.id == task_id))
    return result.scalar_one_or_none()


async def get_tasks_by_owner(
    db: AsyncSession, owner_id: int, skip: int = 0, limit: int = 100
) -> list[Task]:
    result = await db.execute(
        select(Task)
        .where(Task.owner_id == owner_id)
        .order_by(Task.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    return list(result.scalars().all())


async def create_task(db: AsyncSession, task_in: TaskCreate, owner_id: int) -> Task:
    task = Task(
        title=task_in.title,
        description=task_in.description,
        status=task_in.status,
        priority=task_in.priority,
        due_date=task_in.due_date,
        owner_id=owner_id,
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)
    return task


async def update_task(db: AsyncSession, task: Task, task_in: TaskUpdate) -> Task:
    update_data = task_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(task, field, value)
    await db.commit()
    await db.refresh(task)
    return task


async def delete_task(db: AsyncSession, task: Task) -> None:
    await db.delete(task)
    await db.commit()
