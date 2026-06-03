# LS-Matchmaker Backend – Image (Build-Kontext = Repo-Wurzel, dockerfile: backend/Dockerfile)
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app/backend

# Systempakete für psycopg/Builds
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Code + Daten ins Image (für Dev werden backend/ und data/ zusätzlich gemountet)
COPY backend/ /app/backend/
COPY data/ /app/data/

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
