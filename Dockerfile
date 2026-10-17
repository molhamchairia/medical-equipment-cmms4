FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app
COPY requirements.txt ./requirements.txt
RUN pip install --upgrade pip && pip install -r requirements.txt
COPY . .

# Demo data is seeded on container startup. Cloud Run's local filesystem is temporary.
CMD ["sh", "-c", "python -m seed.seed_demo && streamlit run app/main.py --server.address 0.0.0.0 --server.port ${PORT:-8080} --server.headless true"]
