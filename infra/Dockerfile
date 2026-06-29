FROM python:3.11-slim AS base

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY pyproject.toml .
RUN pip install --no-cache-dir -e ".[dev]" || pip install --no-cache-dir .

# Copy application code
COPY contracts/ contracts/
COPY core/ core/
COPY harness/ harness/
COPY pipelines/ pipelines/
COPY agents/ agents/
COPY memory/ memory/
COPY rag/ rag/
COPY app/ app/
COPY proposal_engine_mcp/ proposal_engine_mcp/
COPY policies/ policies/
COPY eval/ eval/
COPY migrations/ migrations/
COPY alembic.ini alembic.ini

# MCP server stage (built explicitly via --target mcp; not the default stage)
FROM base AS mcp
EXPOSE 3100
CMD ["python", "-m", "proposal_engine_mcp"]

# Production stage — kept LAST so platforms that build the final stage by
# default (e.g. Render) get the API. Honors $PORT (Render injects it) and
# falls back to 8000 (ECS task def / docker-compose set PORT=8000).
FROM base AS production
EXPOSE 8000
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
