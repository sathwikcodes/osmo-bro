FROM python:3.11-slim AS base

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
  gcc libpq-dev && \
  apt-get clean && rm -rf /var/lib/apt/lists/*

COPY ./requirements.txt ./
RUN python3 -m pip install --no-cache-dir -r requirements.txt

ENV RUNNING_IN_DOCKER=true

COPY . .

EXPOSE 6969

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "6969"]
