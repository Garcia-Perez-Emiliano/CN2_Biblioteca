FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Dependencias (capa cacheable)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Código del proyecto
COPY . .

# Usuario sin privilegios
RUN useradd --create-home appuser && chown -R appuser /app
USER appuser

EXPOSE 5000

# DATABASE_URL se inyecta como variable de entorno al ejecutar
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "run:app"]