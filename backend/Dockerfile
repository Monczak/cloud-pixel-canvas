FROM ghcr.io/astral-sh/uv:python3.13-alpine

WORKDIR /app

COPY .python-version .
COPY pyproject.toml .
COPY uv.lock .
RUN uv sync --locked

COPY . .

CMD ["uv", "run", "src/main.py"]
