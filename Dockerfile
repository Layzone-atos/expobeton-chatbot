FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements-heroku.txt /app/

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements-heroku.txt

# Copy project files
COPY . /app

# Make scripts executable
RUN chmod +x railway_start.sh render_start.sh static_server.py

# Expose port
EXPOSE 5005

# Start script - auto-detect platform
CMD if [ -f "/etc/render" ] || [ "$RENDER" = "true" ]; then ./render_start.sh; else ./railway_start.sh; fi