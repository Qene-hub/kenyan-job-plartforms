FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# System libraries required to compile the mysqlclient driver
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        pkg-config \
        default-libmysqlclient-dev \
    && rm -rf /var/lib/apt/lists/*

# Install dependencies first so Docker caches this layer
ARG REQUIREMENTS=dev
COPY requirements/ requirements/
RUN pip install --upgrade pip \
    && pip install -r requirements/${REQUIREMENTS}.txt

COPY . .

EXPOSE 8000