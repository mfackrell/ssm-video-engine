FROM python:3.11-slim

# Install only essentials
RUN apt-get update && apt-get install -y \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install static ffmpeg
RUN curl -L https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz \
    | tar -xJ \
    && mv ffmpeg-*/ffmpeg /usr/local/bin/ffmpeg \
    && mv ffmpeg-*/ffprobe /usr/local/bin/ffprobe \
    && rm -rf ffmpeg-*

# Verify
RUN ffmpeg -version

WORKDIR /app
COPY . .
RUN pip install --no-cache-dir -r requirements.txt

CMD ["python", "main.py"]
