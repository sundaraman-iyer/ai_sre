FROM python:3.12-slim

# Memory & CPU optimizations for 512MB RAM free tier (Render.com)
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    OMP_NUM_THREADS=1 \
    MKL_NUM_THREADS=1 \
    TORCH_NUM_THREADS=1 \
    OPENBLAS_NUM_THREADS=1 \
    TOKENIZERS_PARALLELISM=false \
    HF_HOME=/tmp/huggingface \
    PORT=10000

WORKDIR /app

# Install minimal system dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip
RUN pip install --no-cache-dir --upgrade pip

# Install CPU-only PyTorch first (avoids 2.5GB CUDA GPU bloat)
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

# Install ONLY production-required packages (not dev tools, gradio, jupyter, boto3, etc.)
COPY requirements-prod.txt ./
RUN pip install --no-cache-dir -r requirements-prod.txt

# Pre-download sentence-transformers model during build to avoid runtime download
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')"

# Set permissions for cache directory
RUN chmod -R 777 /tmp

# Copy ONLY required application files
COPY main.py week1_rag.py guardrails.py memory.py ./
COPY data/ ./data/

# Expose port
EXPOSE 10000

# Run FastAPI with Uvicorn
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-10000}"]
