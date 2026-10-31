FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    EMBEDDING_CACHE=/opt/models \
    CHROMA_PATH=/data/chroma \
    DATA_DIR=/app/data

WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install -r requirements.txt

# Scarica il modello di embedding multilingue già in fase di build:
# l'avvio del container sarà immediato e non dipenderà dalla rete.
RUN python -c "from fastembed import TextEmbedding; TextEmbedding('sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2', cache_dir='/opt/models')"

COPY app ./app
COPY data ./data
RUN mkdir -p /data/chroma

EXPOSE 8000

# 1) il seeder popola ChromaDB  2) solo dopo parte il backend
CMD ["sh", "-c", "python -m app.seeder && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
