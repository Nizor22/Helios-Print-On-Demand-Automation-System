FROM python:3.13-slim

WORKDIR /app

# Copy the entire project
COPY . .

# Install the helios package in editable mode
RUN pip install -e .

# Install dependencies
RUN pip install -r deployment/run/agents/requirements.txt

# Expose port
EXPOSE 8080

# Set environment variables
ENV PORT=8080
ENV PYTHONPATH=/app

# Run the application
CMD ["python", "-m", "gunicorn", "--bind", "0.0.0.0:8080", "--workers", "4", "--worker-class", "uvicorn.workers.UvicornWorker", "server_ai_agents:app"]
