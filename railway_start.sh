#!/bin/bash

echo "🚀 Démarrage Rasa sur Railway..."
echo "Port Railway: $PORT"

# Entraînement
echo "Entraînement du modèle..."
rasa train --fixed-model-name expobeton-railway --out models/

# Vérifier si le modèle a été créé
if [ ! -f "models/expobeton-railway.tar.gz" ]; then
    echo "❌ Erreur : Le modèle n'a pas été créé!"
    ls -la models/
    exit 1
fi

echo "✅ Modèle entraîné avec succès"

# Démarrage sur le port Railway
echo "Démarrage du serveur Rasa sur le port $PORT..."
rasa run --enable-api --cors "*" --port $PORT --debug -i 0.0.0.0 --model models/expobeton-railway.tar.gz