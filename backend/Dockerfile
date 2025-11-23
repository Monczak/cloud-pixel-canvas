FROM ghcr.io/astral-sh/uv:python3.13-trixie-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY .python-version .
COPY pyproject.toml .
COPY uv.lock .
RUN uv sync --locked

COPY . .

CMD ["uv", "run", "src/main.py"]
