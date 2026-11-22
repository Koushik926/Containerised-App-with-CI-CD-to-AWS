#!/bin/bash
set -euo pipefail

echo "TaskFlow API - Container Starting"
echo "=================================="
echo "Version: ${APP_VERSION:-unknown}"
echo "Git SHA: ${GIT_SHA:-unknown}"
echo "Build Time: ${BUILD_TIME:-unknown}"
echo ""

# Wait for database to be ready
wait_for_db() {
    local max_attempts=30
    local attempt=1

    echo "Waiting for database to be ready..."

    while [ $attempt -le $max_attempts ]; do
        if python -c "
import sys
import asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
import os

async def check():
    try:
        engine = create_async_engine(os.environ['DATABASE_URL'])
        async with engine.connect() as conn:
            await conn.execute(text('SELECT 1'))
        await engine.dispose()
        return True
    except Exception:
        return False

sys.exit(0 if asyncio.run(check()) else 1)
" 2>/dev/null; then
            echo "Database is ready!"
            return 0
        fi

        echo "Attempt $attempt/$max_attempts - Database not ready, waiting..."
        sleep 2
        attempt=$((attempt + 1))
    done

    echo "ERROR: Database did not become ready in time"
    return 1
}

# Run database migrations if enabled
run_migrations() {
    if [ "${RUN_MIGRATIONS:-false}" = "true" ]; then
        echo "Running database migrations..."
        alembic upgrade head
        echo "Migrations complete!"
    else
        echo "Skipping migrations (RUN_MIGRATIONS not set to true)"
    fi
}

# Main startup sequence
main() {
    wait_for_db
    run_migrations

    echo ""
    echo "Starting application..."
    echo "=================================="

    # Execute the CMD
    exec "$@"
}

main "$@"
