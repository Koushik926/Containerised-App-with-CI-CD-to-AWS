import pytest
from httpx import AsyncClient


class TestCreateTask:
    @pytest.mark.asyncio
    async def test_create_task_success(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        response = await client.post(
            "/api/v1/tasks",
            json={"title": "Test Task", "description": "Test description"},
            headers=auth_headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "Test Task"
        assert data["description"] == "Test description"
        assert data["status"] == "todo"
        assert data["priority"] == "medium"
        assert "id" in data
        assert "owner_id" in data

    @pytest.mark.asyncio
    async def test_create_task_with_all_fields(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        response = await client.post(
            "/api/v1/tasks",
            json={
                "title": "Full Task",
                "description": "Full description",
                "status": "in_progress",
                "priority": "high",
                "due_date": "2024-12-31T23:59:59Z",
            },
            headers=auth_headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "in_progress"
        assert data["priority"] == "high"
        assert data["due_date"] is not None

    @pytest.mark.asyncio
    async def test_create_task_minimal(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        response = await client.post(
            "/api/v1/tasks",
            json={"title": "Minimal Task"},
            headers=auth_headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["description"] is None
        assert data["due_date"] is None

    @pytest.mark.asyncio
    async def test_create_task_no_auth(self, client: AsyncClient) -> None:
        response = await client.post(
            "/api/v1/tasks",
            json={"title": "Test Task"},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_create_task_empty_title(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        response = await client.post(
            "/api/v1/tasks",
            json={"title": ""},
            headers=auth_headers,
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_create_task_invalid_status(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        response = await client.post(
            "/api/v1/tasks",
            json={"title": "Test", "status": "invalid"},
            headers=auth_headers,
        )
        assert response.status_code == 422


class TestListTasks:
    @pytest.mark.asyncio
    async def test_list_tasks_empty(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        response = await client.get("/api/v1/tasks", headers=auth_headers)
        assert response.status_code == 200
        assert response.json() == []

    @pytest.mark.asyncio
    async def test_list_tasks_with_tasks(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        await client.post("/api/v1/tasks", json={"title": "Task 1"}, headers=auth_headers)
        await client.post("/api/v1/tasks", json={"title": "Task 2"}, headers=auth_headers)

        response = await client.get("/api/v1/tasks", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 2

    @pytest.mark.asyncio
    async def test_list_tasks_pagination(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        for i in range(5):
            await client.post("/api/v1/tasks", json={"title": f"Task {i}"}, headers=auth_headers)

        response = await client.get(
            "/api/v1/tasks", params={"skip": 0, "limit": 2}, headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2

    @pytest.mark.asyncio
    async def test_list_tasks_no_auth(self, client: AsyncClient) -> None:
        response = await client.get("/api/v1/tasks")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_list_tasks_isolation(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        auth_headers_user2: dict[str, str],
    ) -> None:
        await client.post("/api/v1/tasks", json={"title": "User1 Task"}, headers=auth_headers)
        await client.post("/api/v1/tasks", json={"title": "User2 Task"}, headers=auth_headers_user2)

        response1 = await client.get("/api/v1/tasks", headers=auth_headers)
        response2 = await client.get("/api/v1/tasks", headers=auth_headers_user2)

        titles1 = [t["title"] for t in response1.json()]
        titles2 = [t["title"] for t in response2.json()]

        assert "User1 Task" in titles1
        assert "User2 Task" not in titles1
        assert "User2 Task" in titles2
        assert "User1 Task" not in titles2

    @pytest.mark.asyncio
    async def test_list_tasks_filter_by_status(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        await client.post(
            "/api/v1/tasks",
            json={"title": "Todo Task", "status": "todo"},
            headers=auth_headers,
        )
        await client.post(
            "/api/v1/tasks",
            json={"title": "Done Task", "status": "done"},
            headers=auth_headers,
        )

        response = await client.get(
            "/api/v1/tasks", params={"status": "done"}, headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert all(t["status"] == "done" for t in data)
        assert any(t["title"] == "Done Task" for t in data)

    @pytest.mark.asyncio
    async def test_list_tasks_filter_by_priority(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        await client.post(
            "/api/v1/tasks",
            json={"title": "High Priority", "priority": "high"},
            headers=auth_headers,
        )
        await client.post(
            "/api/v1/tasks",
            json={"title": "Low Priority", "priority": "low"},
            headers=auth_headers,
        )

        response = await client.get(
            "/api/v1/tasks", params={"priority": "high"}, headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert all(t["priority"] == "high" for t in data)

    @pytest.mark.asyncio
    async def test_list_tasks_sort_by_created_at(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        await client.post("/api/v1/tasks", json={"title": "First"}, headers=auth_headers)
        await client.post("/api/v1/tasks", json={"title": "Second"}, headers=auth_headers)

        response_desc = await client.get(
            "/api/v1/tasks",
            params={"sort_by": "created_at", "sort_order": "desc"},
            headers=auth_headers,
        )
        assert response_desc.status_code == 200
        data_desc = response_desc.json()
        if len(data_desc) >= 2:
            assert data_desc[0]["created_at"] >= data_desc[1]["created_at"]

        response_asc = await client.get(
            "/api/v1/tasks",
            params={"sort_by": "created_at", "sort_order": "asc"},
            headers=auth_headers,
        )
        assert response_asc.status_code == 200
        data_asc = response_asc.json()
        if len(data_asc) >= 2:
            assert data_asc[0]["created_at"] <= data_asc[1]["created_at"]

    @pytest.mark.asyncio
    async def test_list_tasks_sort_by_due_date(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        await client.post(
            "/api/v1/tasks",
            json={"title": "Later", "due_date": "2025-12-31T23:59:59Z"},
            headers=auth_headers,
        )
        await client.post(
            "/api/v1/tasks",
            json={"title": "Sooner", "due_date": "2025-01-01T00:00:00Z"},
            headers=auth_headers,
        )
        await client.post(
            "/api/v1/tasks",
            json={"title": "No Due Date"},
            headers=auth_headers,
        )

        response = await client.get(
            "/api/v1/tasks",
            params={"sort_by": "due_date", "sort_order": "asc"},
            headers=auth_headers,
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_list_tasks_combined_filters(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        await client.post(
            "/api/v1/tasks",
            json={"title": "High Todo", "status": "todo", "priority": "high"},
            headers=auth_headers,
        )
        await client.post(
            "/api/v1/tasks",
            json={"title": "High Done", "status": "done", "priority": "high"},
            headers=auth_headers,
        )
        await client.post(
            "/api/v1/tasks",
            json={"title": "Low Todo", "status": "todo", "priority": "low"},
            headers=auth_headers,
        )

        response = await client.get(
            "/api/v1/tasks",
            params={"status": "todo", "priority": "high"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        for task in data:
            assert task["status"] == "todo"
            assert task["priority"] == "high"


class TestGetTask:
    @pytest.mark.asyncio
    async def test_get_task_success(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        create_response = await client.post(
            "/api/v1/tasks", json={"title": "Get Test"}, headers=auth_headers
        )
        task_id = create_response.json()["id"]

        response = await client.get(f"/api/v1/tasks/{task_id}", headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["title"] == "Get Test"

    @pytest.mark.asyncio
    async def test_get_task_not_found(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        response = await client.get("/api/v1/tasks/99999", headers=auth_headers)
        assert response.status_code == 404
        assert response.json()["detail"] == "Task not found"

    @pytest.mark.asyncio
    async def test_get_task_other_user(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        auth_headers_user2: dict[str, str],
    ) -> None:
        create_response = await client.post(
            "/api/v1/tasks", json={"title": "Private Task"}, headers=auth_headers
        )
        task_id = create_response.json()["id"]

        response = await client.get(f"/api/v1/tasks/{task_id}", headers=auth_headers_user2)
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_task_no_auth(self, client: AsyncClient) -> None:
        response = await client.get("/api/v1/tasks/1")
        assert response.status_code == 401


class TestUpdateTask:
    @pytest.mark.asyncio
    async def test_update_task_success(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        create_response = await client.post(
            "/api/v1/tasks", json={"title": "Original"}, headers=auth_headers
        )
        task_id = create_response.json()["id"]

        response = await client.patch(
            f"/api/v1/tasks/{task_id}",
            json={"title": "Updated", "status": "done"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Updated"
        assert data["status"] == "done"

    @pytest.mark.asyncio
    async def test_update_task_partial(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        create_response = await client.post(
            "/api/v1/tasks",
            json={"title": "Original", "description": "Keep this"},
            headers=auth_headers,
        )
        task_id = create_response.json()["id"]

        response = await client.patch(
            f"/api/v1/tasks/{task_id}",
            json={"priority": "high"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Original"
        assert data["description"] == "Keep this"
        assert data["priority"] == "high"

    @pytest.mark.asyncio
    async def test_update_task_not_found(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        response = await client.patch(
            "/api/v1/tasks/99999",
            json={"title": "Updated"},
            headers=auth_headers,
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_update_task_other_user(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        auth_headers_user2: dict[str, str],
    ) -> None:
        create_response = await client.post(
            "/api/v1/tasks", json={"title": "Private"}, headers=auth_headers
        )
        task_id = create_response.json()["id"]

        response = await client.patch(
            f"/api/v1/tasks/{task_id}",
            json={"title": "Hacked"},
            headers=auth_headers_user2,
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_update_task_no_auth(self, client: AsyncClient) -> None:
        response = await client.patch("/api/v1/tasks/1", json={"title": "Updated"})
        assert response.status_code == 401


class TestDeleteTask:
    @pytest.mark.asyncio
    async def test_delete_task_success(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        create_response = await client.post(
            "/api/v1/tasks", json={"title": "To Delete"}, headers=auth_headers
        )
        task_id = create_response.json()["id"]

        response = await client.delete(f"/api/v1/tasks/{task_id}", headers=auth_headers)
        assert response.status_code == 204

        get_response = await client.get(f"/api/v1/tasks/{task_id}", headers=auth_headers)
        assert get_response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_task_not_found(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        response = await client.delete("/api/v1/tasks/99999", headers=auth_headers)
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_task_other_user(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        auth_headers_user2: dict[str, str],
    ) -> None:
        create_response = await client.post(
            "/api/v1/tasks", json={"title": "Private"}, headers=auth_headers
        )
        task_id = create_response.json()["id"]

        response = await client.delete(f"/api/v1/tasks/{task_id}", headers=auth_headers_user2)
        assert response.status_code == 404

        verify = await client.get(f"/api/v1/tasks/{task_id}", headers=auth_headers)
        assert verify.status_code == 200

    @pytest.mark.asyncio
    async def test_delete_task_no_auth(self, client: AsyncClient) -> None:
        response = await client.delete("/api/v1/tasks/1")
        assert response.status_code == 401
