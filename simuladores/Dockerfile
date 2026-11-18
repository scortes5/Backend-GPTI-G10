# APIs simuladas de Agromet e Instacrops. Se construye desde la raíz del repositorio.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /srv
RUN useradd --create-home --uid 10001 agrotracker
RUN pip install "fastapi>=0.115" "uvicorn[standard]>=0.32"

COPY simuladores ./simuladores
COPY app/data/estaciones_agromet.json ./app/data/estaciones_agromet.json
USER agrotracker

EXPOSE 9000
HEALTHCHECK --interval=10s --timeout=5s --start-period=10s --retries=5 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:9000/health', timeout=4)"

# Un solo proceso: el escenario activo vive en memoria.
CMD ["uvicorn", "simuladores.main:app", "--host", "0.0.0.0", "--port", "9000"]
