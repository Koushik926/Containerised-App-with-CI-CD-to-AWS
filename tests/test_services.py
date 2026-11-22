import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.task import TaskPriority, TaskStatus
from app.schemas.task import TaskCreate, TaskUpdate
from app.schemas.user import UserCreate
from app.services.task import (
    create_task,
    delete_task,
    get_task_by_id,
    get_tasks_by_owner,
    update_task,
)
from app.services.user import (
    authenticate_user,
    create_user,
    get_user_by_email,
    get_user_by_id,
)


class TestUserService:
    @pytest.mark.asyncio
    async def test_get_user_by_email_not_found(self, db_session: AsyncSession) -> None:
        user = await get_user_by_email(db_session, "nonexistent@example.com")
        assert user is None

    @pytest.mark.asyncio
    async def test_get_user_by_id_not_found(self, db_session: AsyncSession) -> None:
        user = await get_user_by_id(db_session, 99999)
        assert user is None

    @pytest.mark.asyncio
    async def test_create_and_get_user(self, db_session: AsyncSession) -> None:
        user_in = UserCreate(
            email="service-test@example.com",
            password="testpassword123",
            full_name="Service Test",
        )
        user = await create_user(db_session, user_in)
        assert user.id is not None
        assert user.email == "service-test@example.com"

        fetched = await get_user_by_id(db_session, user.id)
        assert fetched is not None
        assert fetched.email == user.email

        by_email = await get_user_by_email(db_session, user.email)
        assert by_email is not None
        assert by_email.id == user.id

    @pytest.mark.asyncio
    async def test_authenticate_user_success(self, db_session: AsyncSession) -> None:
        user_in = UserCreate(
            email="auth-test@example.com",
            password="correctpassword",
            full_name="Auth Test",
        )
        await create_user(db_session, user_in)

        user = await authenticate_user(db_session, "auth-test@example.com", "correctpassword")
        assert user is not None
        assert user.email == "auth-test@example.com"

    @pytest.mark.asyncio
    async def test_authenticate_user_wrong_password(self, db_session: AsyncSession) -> None:
        user_in = UserCreate(
            email="auth-wrong@example.com",
            password="correctpassword",
            full_name="Auth Test",
        )
        await create_user(db_session, user_in)

        user = await authenticate_user(db_session, "auth-wrong@example.com", "wrongpassword")
        assert user is None

    @pytest.mark.asyncio
    async def test_authenticate_user_not_found(self, db_session: AsyncSession) -> None:
        user = await authenticate_user(db_session, "nobody@example.com", "anypassword")
        assert user is None


class TestTaskService:
    @pytest.mark.asyncio
    async def test_get_task_by_id_not_found(self, db_session: AsyncSession) -> None:
        task = await get_task_by_id(db_session, 99999)
        assert task is None

    @pytest.mark.asyncio
    async def test_task_crud_operations(self, db_session: AsyncSession) -> None:
        user_in = UserCreate(
            email="task-owner@example.com",
            password="testpassword",
            full_name="Task Owner",
        )
        user = await create_user(db_session, user_in)

        task_in = TaskCreate(
            title="Test Task",
            description="Test Description",
            status=TaskStatus.TODO,
            priority=TaskPriority.HIGH,
        )
        task = await create_task(db_session, task_in, user.id)
        assert task.id is not None
        assert task.title == "Test Task"
        assert task.owner_id == user.id

        fetched = await get_task_by_id(db_session, task.id)
        assert fetched is not None

        tasks = await get_tasks_by_owner(db_session, user.id)
        assert len(tasks) >= 1

        update_in = TaskUpdate(title="Updated Task", status=TaskStatus.DONE)
        updated = await update_task(db_session, task, update_in)
        assert updated.title == "Updated Task"
        assert updated.status == TaskStatus.DONE

        await delete_task(db_session, task)
        deleted = await get_task_by_id(db_session, task.id)
        assert deleted is None

    @pytest.mark.asyncio
    async def test_get_tasks_with_filters(self, db_session: AsyncSession) -> None:
        user_in = UserCreate(
            email="filter-owner@example.com",
            password="testpassword",
            full_name="Filter Owner",
        )
        user = await create_user(db_session, user_in)

        task1 = TaskCreate(title="Task 1", status=TaskStatus.TODO, priority=TaskPriority.HIGH)
        task2 = TaskCreate(title="Task 2", status=TaskStatus.DONE, priority=TaskPriority.LOW)
        await create_task(db_session, task1, user.id)
        await create_task(db_session, task2, user.id)

        todo_tasks = await get_tasks_by_owner(db_session, user.id, status=TaskStatus.TODO)
        assert all(t.status == TaskStatus.TODO for t in todo_tasks)

        high_tasks = await get_tasks_by_owner(db_session, user.id, priority=TaskPriority.HIGH)
        assert all(t.priority == TaskPriority.HIGH for t in high_tasks)

        asc_tasks = await get_tasks_by_owner(db_session, user.id, sort_order="asc")
        assert len(asc_tasks) >= 2

        due_tasks = await get_tasks_by_owner(db_session, user.id, sort_by="due_date")
        assert len(due_tasks) >= 2
