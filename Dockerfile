# Web studio in a container (Hugging Face Docker Space, Render, Railway, any VPS).
#   docker build -t desi-toons . && docker run -p 7860:7860 -e GEMINI_API_KEY=... desi-toons
FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
        ffmpeg fonts-noto-core fonts-noto-color-emoji fonts-liberation libraqm0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN useradd -m app && chown -R app /app
USER app

ENV PYTHONUNBUFFERED=1 PORT=7860
EXPOSE 7860
CMD ["python", "-m", "studio.web", "--host", "0.0.0.0"]
