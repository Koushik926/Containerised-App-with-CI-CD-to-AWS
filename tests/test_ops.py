import logging

import pytest
from httpx import AsyncClient

from app.core.logging import (
    JsonFormatter,
    get_logger,
    get_request_id,
    request_id_ctx,
    setup_logging,
)


class TestLogging:
    def test_get_request_id_default(self) -> None:
        token = request_id_ctx.set(None)
        try:
            assert get_request_id() is None
        finally:
            request_id_ctx.reset(token)

    def test_get_request_id_set(self) -> None:
        token = request_id_ctx.set("test-123")
        try:
            assert get_request_id() == "test-123"
        finally:
            request_id_ctx.reset(token)

    def test_setup_logging_json(self) -> None:
        setup_logging(log_level="DEBUG", json_logs=True)
        logger = get_logger("test")
        assert logger is not None

    def test_setup_logging_text(self) -> None:
        setup_logging(log_level="INFO", json_logs=False)
        logger = get_logger("test")
        assert logger is not None

    def test_json_formatter(self) -> None:
        formatter = JsonFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None,
        )
        output = formatter.format(record)
        assert "Test message" in output
        assert "timestamp" in output

    def test_json_formatter_with_request_id(self) -> None:
        formatter = JsonFormatter()
        token = request_id_ctx.set("req-456")
        try:
            record = logging.LogRecord(
                name="test",
                level=logging.INFO,
                pathname="test.py",
                lineno=1,
                msg="Test message",
                args=(),
                exc_info=None,
            )
            output = formatter.format(record)
            assert "req-456" in output
        finally:
            request_id_ctx.reset(token)

    def test_json_formatter_with_exception(self) -> None:
        formatter = JsonFormatter()
        try:
            raise ValueError("Test error")
        except ValueError:
            import sys

            record = logging.LogRecord(
                name="test",
                level=logging.ERROR,
                pathname="test.py",
                lineno=1,
                msg="Error occurred",
                args=(),
                exc_info=sys.exc_info(),
            )
            output = formatter.format(record)
            assert "exception" in output

    def test_json_formatter_with_extra_fields(self) -> None:
        formatter = JsonFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None,
        )
        record.extra_fields = {"user_id": 123}  # type: ignore[attr-defined]
        output = formatter.format(record)
        assert "user_id" in output


class TestHealthEndpoints:
    @pytest.mark.asyncio
    async def test_health_live(self, client: AsyncClient) -> None:
        response = await client.get("/health/live")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "alive"

    @pytest.mark.asyncio
    async def test_health_ready(self, client: AsyncClient) -> None:
        response = await client.get("/health/ready")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ready"


class TestVersionEndpoint:
    @pytest.mark.asyncio
    async def test_version(self, client: AsyncClient) -> None:
        response = await client.get("/version")
        assert response.status_code == 200
        data = response.json()
        assert "app_name" in data
        assert "version" in data
        assert "git_sha" in data
        assert "build_time" in data
        assert "environment" in data
        assert data["app_name"] == "TaskFlow API"


class TestHomePage:
    @pytest.mark.asyncio
    async def test_home_page(self, client: AsyncClient) -> None:
        response = await client.get("/")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        assert "TaskFlow API" in response.text
        assert "/docs" in response.text


class TestMetricsEndpoint:
    @pytest.mark.asyncio
    async def test_metrics(self, client: AsyncClient) -> None:
        response = await client.get("/metrics")
        assert response.status_code == 200
        assert "http_requests_total" in response.text or "http_request" in response.text
