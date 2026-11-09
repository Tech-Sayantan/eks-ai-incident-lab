FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FASTEMBED_CACHE_PATH=/opt/embedding-models

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY *.py .
COPY fixtures/ fixtures/
RUN python -c 'from orders_rag import embedding_model; next(embedding_model().passage_embed(["warmup"]))' \
    && chmod -R a+rX /opt/embedding-models

USER 10001:10001
CMD ["uvicorn", "investigator_api:app", "--host", "0.0.0.0", "--port", "8080"]
