FROM python:3.11-slim

# ffmpeg für Audio-Verarbeitung (von einigen Plugins erwartet).
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Build-Nachweis: bei jedem Build den Git-Stand mitgeben (Compose:
# --build-arg BUILD_ID=$(git rev-parse --short HEAD)). agent.py loggt ihn beim Start.
# So ist nie unklar, welcher Code laeuft. MERKE: Code-Aenderung => `docker compose up -d --build`,
# NICHT nur `restart` (sonst laeuft alter Image-Code) — agent.py/brain.py sind hier zwar
# Volume-gemountet (restart genuegt), die uebrige Logik aber nicht.
ARG BUILD_ID=dev
ENV BUILD_ID=$BUILD_ID

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

# Plugin-Modelle (z. B. Silero-VAD) vorab laden, damit der erste Lauf nicht hängt.
RUN python agent.py download-files || true

# Worker-Prozess (verbindet sich mit dem LiveKit-Server, wartet auf Räume).
CMD ["python", "agent.py", "start"]
