@echo off
echo Building Docker image...
docker build -f Dockerfile -t rasa-expobeton .

echo Training model...
docker run --rm -v "%cd%:/app" rasa-expobeton rasa train --config config_minimal.yml --fixed-model-name expobeton-railway --out models/

echo Done! Model saved to models/expobeton-railway.tar.gz
pause
