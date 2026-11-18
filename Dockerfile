# API de AgroTracker (FastAPI). Imagen para producción: usuario sin privilegios, sin tests ni .env.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /srv
RUN useradd --create-home --uid 10001 agrotracker

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY app ./app
USER agrotracker

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=4)"

# Un solo proceso: el límite de intentos de login y la caché de Agromet viven en memoria.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips", "*"]
