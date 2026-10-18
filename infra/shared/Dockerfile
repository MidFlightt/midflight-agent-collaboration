FROM python:3.12-slim
WORKDIR /app
RUN pip install --no-cache-dir uv==0.9.4
COPY pyproject.toml uv.lock README.md ./
COPY midflight ./midflight
RUN uv sync --locked --no-dev --extra falkordb
RUN useradd --uid 10001 --create-home midflight
USER midflight
ENV PATH="/app/.venv/bin:$PATH"
CMD ["uvicorn", "midflight.communication.cloud:create_app", "--factory", "--host", "0.0.0.0", "--port", "8080", "--no-access-log", "--limit-concurrency", "64"]
