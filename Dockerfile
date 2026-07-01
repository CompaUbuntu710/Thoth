FROM python:3.14-slim AS builder

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

FROM python:3.14-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    espeak-ng \
    libsndfile1 \
    ffmpeg \
    curl \
    # Playwright system dependencies
    libnss3 libnspr4 libatk1.0-0 libatk-bridge2.0-0 libcups2 libdrm2 \
    libdbus-1-3 libxkbcommon0 libxcomposite1 libxdamage1 libxfixes3 \
    libxrandr2 libgbm1 libpango-1.0-0 libcairo2 libasound2 libatspi2.0-0 \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH

WORKDIR /thoth

COPY core/ core/
COPY api/ api/
COPY memory/ memory/
COPY tools/ tools/
COPY plugins/ plugins/
COPY ui/ ui/
COPY voice/ voice/
COPY .env .
COPY requirements.txt .

RUN playwright install chromium 2>/dev/null || true

ENV PYTHONPATH=/thoth
ENV HOST=0.0.0.0
ENV PORT=8000
ENV REDIS_URL=redis://redis:6379/0
ENV OLLAMA_URL=http://ollama:11434

EXPOSE 8000

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
