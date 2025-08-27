# Use Python 3.11 slim image as base
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt ./pii_service/

# Install Python dependencies
RUN pip install --no-cache-dir -r ./pii_service/requirements.txt

# Download spaCy model
RUN python -m spacy download en_core_web_lg

# Copy the application code
COPY . ./pii_service/

# Create a non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 8000

# Set environment variables for container
ENV PYTHONPATH=/app
ENV GLINER_LOCAL_DIR=/app/pii_service/models/gliner_small-v2.1

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the application
CMD ["python", "-m", "uvicorn", "pii_service.app:app", "--host", "0.0.0.0", "--port", "8000"]
