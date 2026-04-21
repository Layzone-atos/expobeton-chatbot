FROM python:3.10-slim

# Force rebuild - 2026-04-17 19:45 - Use committed model for instant startup
# Model expobeton-railway.tar.gz is committed to git (85.5% accuracy)
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

# Copy project files (includes pre-trained models/expobeton-railway.tar.gz)
COPY . /app

# Make scripts executable AND strip Windows CRLF line endings
# (git on Windows may commit \r\n bytes even with .gitattributes)
RUN sed -i 's/\r$//' railway_start.sh render_start.sh static_server.py && \
    chmod +x railway_start.sh render_start.sh static_server.py && \
    echo "Line endings fixed" && head -1 railway_start.sh | cat -A

# Train model with current rules/stories/NLU data
# Uses config_build.yml (30 epochs) for faster Docker builds
RUN rasa train --config config_build.yml --domain domain.yml --data data/ \
    --out models/ --fixed-model-name expobeton-railway \
    && ls -la models/ && echo "Model training complete"

# Expose port
EXPOSE 5005

# Start script - auto-detect platform
CMD ["/bin/bash", "-c", "if [ -f '/etc/render' ] || [ \"$RENDER\" = 'true' ]; then ./render_start.sh; else ./railway_start.sh; fi"]