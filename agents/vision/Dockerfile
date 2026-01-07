FROM python:3.12-slim

WORKDIR /app

# Install system dependencies for image processing
RUN apt-get update && apt-get install -y \
    build-essential \
    git \
    gcc \
    g++ \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose port (8002 for vision-agent)
EXPOSE 8002

# Run the application
CMD ["uvicorn", "vision_agent:app", "--host", "0.0.0.0", "--port", "8002"]

