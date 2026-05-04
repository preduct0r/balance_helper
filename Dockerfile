FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src \
    BALANCE_STORE_BACKEND=local \
    BALANCE_STORE_PATH=/app/data/local_store.json \
    BALANCE_LOG_FILE=/app/logs/app.jsonl \
    BALANCE_WEB_HOST=0.0.0.0 \
    BALANCE_WEB_PORT=8080

WORKDIR /app

COPY requirements.txt pyproject.toml README.md ./
COPY src ./src

RUN python -m pip install --no-cache-dir --upgrade pip \
    && python -m pip install --no-cache-dir -r requirements.txt

RUN mkdir -p /app/data /app/logs

EXPOSE 8080

CMD ["python", "-m", "balance_fundraising.cli", "web", "--host", "0.0.0.0", "--port", "8080"]
