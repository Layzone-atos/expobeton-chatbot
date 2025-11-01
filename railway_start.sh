#!/bin/bash

echo "🚀 Démarrage Rasa sur Railway..."
echo "Port Railway: $PORT"

# Entraînement du modèle
echo "Entraînement du modèle..."
rasa train --config config_simple.yml --fixed-model-name expobeton-railway --out models/

# Vérifier si le modèle a été créé
if [ ! -f "models/expobeton-railway.tar.gz" ]; then
    echo "❌ Erreur : Le modèle n'a pas été créé!"
    ls -la models/
    exit 1
fi

echo "✅ Modèle entraîné avec succès"

# Démarrage du serveur combiné qui gère à la fois l'API Rasa et l'interface web
echo "Démarrage du serveur combiné sur le port $PORT..."
python combined_server.py