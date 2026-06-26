FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt requirements-dev.txt pyproject.toml ./
COPY app ./app
COPY migrations ./migrations
COPY wsgi.py ./

RUN pip install --no-cache-dir -r requirements-dev.txt && pip install --no-cache-dir -e .

ENV FLASK_APP=wsgi:app
ENV PYTHONUNBUFFERED=1

EXPOSE 5000

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "wsgi:app"]
