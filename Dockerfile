FROM python:3.11-slim

# Install system dependencies (ffmpeg + basics)
RUN apt-get update && apt-get install -y \
    ffmpeg \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy code
COPY main.py .

# Install Python deps (add later as needed)
RUN pip install --no-cache-dir \
    google-cloud-storage \
    flask

# Cloud Run uses PORT
ENV PORT=8080

# Start the app
CMD ["python", "main.py"]
