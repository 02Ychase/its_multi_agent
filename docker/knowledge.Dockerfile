FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY backend/knowledge/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY backend/knowledge/ .

# Copy knowledge data
COPY backend/knowledge/data/ ./data/
COPY backend/knowledge/chroma_kb1/ ./chroma_kb1/

# Expose port
EXPOSE 8001

# Run the application
CMD ["uvicorn", "api.main:create_fast_api", "--host", "0.0.0.0", "--port", "8001", "--factory"]
