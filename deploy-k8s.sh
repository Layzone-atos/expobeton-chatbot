#!/bin/bash

# Script de déploiement pour ExpoBeton Chatbot sur Kubernetes

echo "🚀 Déploiement du chatbot ExpoBeton sur Kubernetes"

# Créer le namespace
echo "🔧 Création du namespace..."
kubectl create namespace expobeton --dry-run=client -o yaml | kubectl apply -f -

# Appliquer les secrets (à personnaliser)
echo "🔑 Configuration des secrets..."
kubectl apply -f k8s/secrets.yaml -n expobeton

# Créer le ConfigMap pour les actions
echo "⚙️  Configuration des actions..."
kubectl apply -f k8s/actions-configmap.yaml -n expobeton

# Créer le ConfigMap pour le contenu web
echo "🌐 Configuration du contenu web..."
kubectl apply -f k8s/web-configmap.yaml -n expobeton

# Créer le ConfigMap pour Caddy
echo "🏠 Configuration de Caddy..."
kubectl apply -f k8s/caddy-configmap.yaml -n expobeton

# Créer le ConfigMap pour les modèles (à personnaliser avec votre modèle)
echo "🧠 Configuration des modèles..."
kubectl create configmap rasa-models --from-file=models/expobeton-french.tar.gz -n expobeton --dry-run=client -o yaml | kubectl apply -f -

# Déployer les services
echo "サービ Déploiement des services..."
kubectl apply -f k8s/rasa-deployment.yaml -n expobeton
kubectl apply -f k8s/actions-deployment.yaml -n expobeton
kubectl apply -f k8s/web-deployment.yaml -n expobeton

# Attendre que les services soient prêts
echo "⏱️  Attente de la disponibilité des services..."
kubectl wait --for=condition=available --timeout=600s deployment/expobeton-rasa -n expobeton
kubectl wait --for=condition=available --timeout=600s deployment/expobeton-actions -n expobeton
kubectl wait --for=condition=available --timeout=600s deployment/expobeton-web -n expobeton

echo "✅ Déploiement terminé!"
echo "📊 Vérification des services:"
kubectl get services -n expobeton
echo "📦 Vérification des pods:"
kubectl get pods -n expobeton

echo "🌐 Accédez à votre chatbot via l'IP externe du service expobeton-web-service"