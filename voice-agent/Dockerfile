FROM python:3.11-slim

# ffmpeg für Audio-Verarbeitung (von einigen Plugins erwartet).
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

# Plugin-Modelle (z. B. Silero-VAD) vorab laden, damit der erste Lauf nicht hängt.
RUN python agent.py download-files || true

# Worker-Prozess (verbindet sich mit dem LiveKit-Server, wartet auf Räume).
CMD ["python", "agent.py", "start"]
