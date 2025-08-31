FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app

# minimal deps for building llama-cpp wheel with OpenBLAS
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential cmake libopenblas-dev curl && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/
# Enable BLAS acceleration in llama.cpp (portable on CPU)
ENV CMAKE_ARGS="-DLLAMA_BLAS=ON -DLLAMA_BLAS_VENDOR=OpenBLAS"
RUN pip install --no-cache-dir -r requirements.txt

# copy just the app code (models are mounted as a volume)
COPY app.py /app/

# Create models directory
RUN mkdir -p /app/models/llamaguard-7b-gguf

EXPOSE 8003
CMD ["python","-m","uvicorn","app:app","--host","0.0.0.0","--port","8003","--log-level","info"]
