FROM ghcr.io/astral-sh/uv:python3.13-alpine

WORKDIR /app

COPY . .
RUN uv sync --locked

CMD ["uv", "run", "main.py"]
