FROM python:3.11-slim AS base

WORKDIR /app

COPY ./requirements.txt ./
RUN python3 -m pip install --no-cache-dir -r requirements.txt

ENV RUNNING_IN_DOCKER=true

COPY . .

RUN useradd --create-home --uid 10001 appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD python3 -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/healthz', timeout=3)"

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
