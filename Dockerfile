FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    && rm -rf /var/lib/apt/lists/*

RUN pip install uv

COPY pyproject.toml uv.lock README.md ./
COPY src/ ./src/
COPY cli/ ./cli/
COPY main.py ./
COPY config.ini ./

RUN uv sync

RUN uv run playwright install chromium
RUN uv run playwright install-deps chromium

RUN mkdir -p data logs

ENTRYPOINT ["uv", "run", "python", "main.py"]
