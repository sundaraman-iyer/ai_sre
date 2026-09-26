FROM python:3.12-slim

# Memory & CPU optimizations for 512MB RAM free tier (Render.com)
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    OMP_NUM_THREADS=1 \
    MKL_NUM_THREADS=1 \
    OPENBLAS_NUM_THREADS=1 \
    TOKENIZERS_PARALLELISM=false \
    HF_HOME=/tmp/huggingface \
    PORT=10000

WORKDIR /app

# Upgrade pip only (no system packages needed for fastembed/ONNX)
RUN pip install --no-cache-dir --upgrade pip

# Install ONLY production-required packages
# fastembed uses ONNX runtime - NO torch, NO CUDA, NO scipy, NO scikit-learn
COPY requirements-prod.txt ./
RUN pip install --no-cache-dir -r requirements-prod.txt

# Pre-download the ONNX embedding model during build (not at runtime)
RUN python -c "from fastembed import TextEmbedding; TextEmbedding('sentence-transformers/all-MiniLM-L6-v2')"

# Set permissions for cache directory
RUN chmod -R 777 /tmp

# Copy ONLY required application files
COPY main.py week1_rag.py guardrails.py memory.py ./
COPY data/ ./data/

# Expose port
EXPOSE 10000

# Run FastAPI with Uvicorn
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-10000}"]
