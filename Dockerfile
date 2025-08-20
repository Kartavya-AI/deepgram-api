# Use Python 3.11 slim image as base
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install cloudflared
RUN curl -L --output cloudflared.deb https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb \
    && dpkg -i cloudflared.deb \
    && rm cloudflared.deb

# Copy requirements or install dependencies directly
# If you have a requirements.txt, uncomment the next two lines:
# COPY requirements.txt .
# RUN pip install --no-cache-dir -r requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir websockets certifi

# Copy your application code
COPY server.py .

# Expose the port your server runs on
EXPOSE 5000

# Create a startup script that runs both the server and cloudflared tunnel
RUN echo '#!/bin/bash\n\
# Start the Python server in the background\n\
python3 server.py &\n\
\n\
# Wait a moment for the server to start\n\
sleep 2\n\
\n\
# Start cloudflared tunnel in the foreground\n\
cloudflared tunnel --url http://localhost:5000' > /app/start.sh \
    && chmod +x /app/start.sh

# Run the startup script
CMD ["/app/start.sh"]