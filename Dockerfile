# Stage 1: Build stage
FROM --platform=linux/amd64 python:3.13-slim AS build-stage

ENV PYTHONFAULTHANDLER=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONHASHSEED=random \
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_DEFAULT_TIMEOUT=100 \
    POETRY_VERSION=1.1.14

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    nginx \
    certbot \
    python3-certbot-nginx \
    curl \
    wget \
    gcc \
    cron \
    procps \
    libicu-dev \
    pkg-config \
    build-essential \
    net-tools \
    dnsutils \
    musl-dev \
    libpq-dev \
    postgresql-client \
    osm2pgsql \
    netcat-traditional \
    inetutils-ping \
    telnet \
    ntp \
    && rm -rf /var/lib/apt/lists/*

# Install dependencies required by Playwright
RUN apt-get update && apt-get install -y \
    libnss3 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libdrm2 \
    libxkbcommon0 \
    libx11-xcb1 \
    libxcb-dri3-0 \
    libxcomposite1 \
    libxdamage1 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    libxshmfence1 \
    libwayland-server0 \
    libwayland-client0 \
    && rm -rf /var/lib/apt/lists/*

# Install Playwright browsers
RUN pip install playwright && playwright install --with-deps chromium

# Install NTP
RUN ntpd -gq
ENV TZ=Europe/Vienna
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# Install Poetry and Python dependencies
RUN pip install --upgrade pip \
  && pip install gunicorn \
  && pip install poetry \
  && pip install psycopg2-binary

# Copy the entire project directory
COPY . /code
WORKDIR /code
RUN mkdir /code/data/tickets

RUN ls -la

RUN if [ -f .env ]; then cat .env; fi

# Project initialization:
RUN rm -rf /code/.venv && poetry config virtualenvs.create false && poetry install --no-interaction --no-ansi --no-root

# Temp Environment Workaround
COPY .env.devel .env

# Expose ports
EXPOSE 80 443

CMD ["gunicorn", "-k", "uvicorn.workers.UvicornWorker", "backend.main:app", "--bind", "0.0.0.0:80"]
