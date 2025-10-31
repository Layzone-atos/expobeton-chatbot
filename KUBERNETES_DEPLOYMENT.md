# Déploiement Kubernetes pour ExpoBeton Chatbot

Ce guide explique comment déployer le chatbot ExpoBeton sur un cluster Kubernetes.

## Prérequis

1. Un cluster Kubernetes opérationnel
2. `kubectl` configuré pour accéder à votre cluster
3. Docker (pour builder les images si nécessaire)
4. Helm (optionnel, pour le déploiement via Helm)

## Structure du déploiement

```
k8s/
├── rasa-deployment.yaml       # Serveur Rasa
├── actions-deployment.yaml    # Action Server
├── web-deployment.yaml        # Interface web
├── secrets.yaml              # Secrets (à personnaliser)
├── actions-configmap.yaml    # Code des actions
├── web-configmap.yaml        # Contenu web
├── caddy-configmap.yaml      # Configuration Caddy
└── models-configmap.yaml     # Modèles Rasa
```

## Configuration initiale

1. **Personnaliser les secrets** dans `k8s/secrets.yaml`:
   ```bash
   # Encoder vos valeurs en base64
   echo -n 'votre_cle_api' | base64
   ```

2. **Vérifier le modèle** dans `models/expobeton-french.tar.gz`

## Déploiement

### Méthode 1: Scripts Kubernetes

```bash
# Rendre le script exécutable
chmod +x deploy-k8s.sh

# Exécuter le déploiement
./deploy-k8s.sh
```

### Méthode 2: Commandes manuelles

```bash
# Créer le namespace
kubectl create namespace expobeton

# Appliquer les configurations
kubectl apply -f k8s/ -n expobeton

# Vérifier le déploiement
kubectl get pods -n expobeton
```

## Accès aux services

Après le déploiement, vous pouvez accéder aux services via:

- **Interface web**: `http://<EXTERNAL-IP>:80`
- **API Rasa**: `http://<EXTERNAL-IP>:5005`
- **Action Server**: Accessible en interne via `expobeton-actions-service:5055`

## Mise à jour

Pour mettre à jour le déploiement:

```bash
# Mettre à jour le modèle
kubectl create configmap rasa-models --from-file=models/expobeton-french.tar.gz -n expobeton -o yaml --dry-run=client | kubectl apply -f -

# Redémarrer les pods
kubectl rollout restart deployment/expobeton-rasa -n expobeton
```

## Monitoring

```bash
# Voir les logs
kubectl logs -f deployment/expobeton-rasa -n expobeton

# Vérifier les ressources
kubectl top pods -n expobeton
```

## Suppression

Pour supprimer complètement le déploiement:

```bash
kubectl delete namespace expobeton
```