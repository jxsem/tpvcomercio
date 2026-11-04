FROM python:3.14-slim

# Sin .pyc ni buffer en stdout: los logs salen al instante en `docker logs`.
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1

WORKDIR /app

# Primero las dependencias: si solo cambia el código, esta capa se reutiliza.
COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

COPY alembic.ini .
COPY backend backend

# El contenedor no corre como root.
RUN useradd --create-home appuser
USER appuser

EXPOSE 8000
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
