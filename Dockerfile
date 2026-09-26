FROM python:3.12-slim

# Memory & CPU optimizations for 512MB RAM free tier limits (Render/Koyeb)
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONMALLOC=malloc \
    OMP_NUM_THREADS=1 \
    MKL_NUM_THREADS=1 \
    TORCH_NUM_THREADS=1 \
    OPENBLAS_NUM_THREADS=1 \
    HF_HOME=/tmp/huggingface \
    PORT=10000

WORKDIR /app

# Install minimal system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency files
COPY pyproject.toml requirements.txt ./

# Install CPU-only PyTorch first to eliminate 2.5GB CUDA GPU bloat and drop RAM usage below 150MB
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu && \
    pip install --no-cache-dir -r requirements.txt

# Pre-download sentence-transformers model to optimize startup time
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')"

# Set permissions for HF cache directory
RUN chmod -R 777 /tmp

# Copy application files
COPY main.py week1_rag.py guardrails.py memory.py app.py ./
COPY data/ ./data/
COPY evals/ ./evals/

# Expose default port
EXPOSE 10000

# Run FastAPI app with Uvicorn respecting dynamic PORT environment variable
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-10000}"]
