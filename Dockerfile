# Use Python 3.11 slim image for compatibility
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Install the helios package in development mode
RUN pip install -e .

# Expose port
EXPOSE 8080

# Set environment variable
ENV PORT=8080

# Use the Procfile command
CMD ["gunicorn", "--bind", ":8080", "--workers", "4", "--worker-class", "uvicorn.workers.UvicornWorker", "main:app"]
