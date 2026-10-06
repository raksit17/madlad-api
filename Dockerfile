FROM pytorch/pytorch:2.14.0-cuda12.6-cudnn9-runtime

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_BREAK_SYSTEM_PACKAGES=1 \
    HF_HOME=/models/huggingface

# Install dependencies first for Docker layer caching
COPY requirements.txt .

RUN python -m pip install --no-cache-dir -r requirements.txt

# Copy application
COPY app ./app

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]