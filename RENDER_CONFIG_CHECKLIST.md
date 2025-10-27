# ✅ Checklist de Configuration Render.com - ExpoBeton Chatbot

## 📊 État Actuel de la Configuration

### ✅ **PRÊT:**
- [x] Code poussé sur GitHub: https://github.com/Layzone-atos/expobeton-chatbot
- [x] Dockerfile.actions configuré
- [x] Dockerfile.rasa configuré
- [x] Structure du projet correcte

### ⏳ **EN COURS:**
- [ ] Modèle Rasa en cours d'entraînement (`expobeton-french.tar.gz`)

### ⚠️ **À FAIRE:**
- [ ] Pousser le modèle entraîné sur GitHub
- [ ] Corriger endpoints.yml pour Render
- [ ] Déployer sur Render.com

---

## 🚀 **GUIDE DE DÉPLOIEMENT - 3 SERVICES**

### **SERVICE 1: Action Server** 🔧

#### Configuration Render:
```yaml
Type: Web Service
Runtime: Docker ⭐
Repository: Layzone-atos/expobeton-chatbot
```

#### Paramètres:
| Paramètre | Valeur |
|-----------|--------|
| **Name** | `expobeton-actions` |
| **Region** | `Frankfurt (EU Central)` |
| **Branch** | `main` |
| **Runtime** | **Docker** ⚠️ PAS Python! |
| **Dockerfile Path** | `Dockerfile.actions` ⭐ |
| **Instance Type** | `Free` |

#### Variables d'Environnement:
```env
COHERE_API_KEY = [votre clé Cohere]
SMTP_SERVER = smtp.gmail.com
SMTP_PORT = 587
SMTP_USERNAME = bot@expobetonrdc.com
SMTP_PASSWORD = [mot de passe app Gmail 16 caractères]
NOTIFICATION_EMAIL = info@expobetonrdc.com
```

#### URL Résultante:
`https://expobeton-actions.onrender.com` ✅

---

### **SERVICE 2: Rasa Server** 🤖

#### Configuration Render:
```yaml
Type: Web Service
Runtime: Docker ⭐
Repository: Layzone-atos/expobeton-chatbot
```

#### Paramètres:
| Paramètre | Valeur |
|-----------|--------|
| **Name** | `expobeton-rasa` |
| **Region** | `Frankfurt (EU Central)` |
| **Branch** | `main` |
| **Runtime** | **Docker** ⚠️ PAS Python! |
| **Dockerfile Path** | `Dockerfile.rasa` ⭐ |
| **Instance Type** | `Free` |

#### Variables d'Environnement:
```env
ACTION_ENDPOINT_URL = https://expobeton-actions.onrender.com/webhook
RASA_MODEL = /app/models/expobeton-french.tar.gz
```

⚠️ **IMPORTANT:** Attendez que le Service 1 (actions) soit déployé avant de créer celui-ci!

#### URL Résultante:
`https://expobeton-rasa.onrender.com` ✅

---

### **SERVICE 3: Site Web** 🌐

#### Configuration Render:
```yaml
Type: Static Site ⭐ (PAS Web Service!)
Repository: Layzone-atos/expobeton-chatbot
```

#### Paramètres:
| Paramètre | Valeur |
|-----------|--------|
| **Name** | `expobeton-web` |
| **Branch** | `main` |
| **Build Command** | (vide) |
| **Publish Directory** | `web` ⭐ |

#### URL Résultante:
`https://expobeton-web.onrender.com` ✅

---

## 🔧 **MODIFICATIONS À FAIRE AVANT DÉPLOIEMENT**

### 1. Corriger endpoints.yml

**Fichier:** `endpoints.yml`

**Changer:**
```yaml
action_endpoint:
  url: "http://localhost:5055/webhook"
```

**En:**
```yaml
action_endpoint:
  url: "${ACTION_ENDPOINT_URL}"
```

### 2. Vérifier que le modèle sera poussé

Après l'entraînement, vérifier que `models/expobeton-french.tar.gz` existe, puis:

```bash
git add models/expobeton-french.tar.gz
git commit -m "Add trained Rasa model"
git push origin main
```

---

## 📋 **ORDRE DE DÉPLOIEMENT (IMPORTANT!)**

### Étape 1: Déployer Action Server
1. Créer service `expobeton-actions`
2. Configurer variables d'environnement
3. Attendre déploiement ✅
4. Noter l'URL: `https://expobeton-actions.onrender.com`

### Étape 2: Déployer Rasa Server
1. Créer service `expobeton-rasa`
2. Utiliser l'URL du Service 1 dans `ACTION_ENDPOINT_URL`
3. Attendre déploiement ✅
4. Noter l'URL: `https://expobeton-rasa.onrender.com`

### Étape 3: Mettre à jour Chat Widget
1. Éditer `web/chat-widget.js`
2. Remplacer l'URL Rasa par celle du Service 2
3. Push sur GitHub

### Étape 4: Déployer Site Web
1. Créer static site `expobeton-web`
2. Attendre déploiement ✅
3. Tester le chatbot!

---

## ⚠️ **ERREURS COURANTES À ÉVITER**

### ❌ Erreur 1: Choisir "Python 3" au lieu de "Docker"
**Solution:** Dans "Runtime", sélectionnez **Docker**, pas Python!

### ❌ Erreur 2: Oublier le Dockerfile Path
**Solution:** Spécifiez `Dockerfile.actions` ou `Dockerfile.rasa`

### ❌ Erreur 3: Mauvais ordre de déploiement
**Solution:** Toujours déployer Actions AVANT Rasa!

### ❌ Erreur 4: Modèle manquant
**Solution:** Vérifiez que `models/expobeton-french.tar.gz` existe sur GitHub

### ❌ Erreur 5: Variables d'environnement manquantes
**Solution:** Ajoutez TOUTES les variables listées ci-dessus

---

## 🧪 **TESTS APRÈS DÉPLOIEMENT**

### Test 1: Action Server
```bash
curl https://expobeton-actions.onrender.com/health
```
Devrait retourner un statut 200

### Test 2: Rasa Server
```bash
curl https://expobeton-rasa.onrender.com/
```
Devrait retourner la version Rasa

### Test 3: Chatbot Complet
1. Visitez `https://expobeton-web.onrender.com`
2. Cliquez sur le bouton chat
3. Testez en français: "Bonjour, je m'appelle Louis"
4. Testez en anglais: "Hello, how are you?"
5. Testez les feedbacks

---

## 📊 **MONITORING**

### Vérifier les Logs
Dans le dashboard Render:
1. Sélectionnez le service
2. Onglet **Logs**
3. Recherchez les erreurs

### Logs Importants
- Action Server: `rasa run actions`
- Rasa Server: `Starting Rasa server`
- Erreurs: `ERROR`, `Failed`, `ModuleNotFoundError`

---

## 🆘 **DÉPANNAGE**

### Problème: "Module 'actions' not found"
**Cause:** Dockerfile.actions mal configuré
**Solution:** Vérifiez que `COPY actions /app/actions` est présent

### Problème: "Model not found"
**Cause:** Modèle pas sur GitHub
**Solution:** 
```bash
git add models/expobeton-french.tar.gz
git push
```

### Problème: "Action endpoint unreachable"
**Cause:** Mauvaise URL dans endpoints.yml
**Solution:** Utilisez l'URL Render, pas localhost

### Problème: Service dort après 15 min
**Cause:** Free tier de Render
**Solution:** Utilisez UptimeRobot pour ping toutes les 5 min

---

## ✅ **CHECKLIST FINALE**

Avant de déployer, vérifiez:

- [ ] Modèle `expobeton-french.tar.gz` existe et poussé sur GitHub
- [ ] `Dockerfile.actions` présent
- [ ] `Dockerfile.rasa` présent
- [ ] `endpoints.yml` utilise variable d'environnement
- [ ] Variables SMTP configurées
- [ ] Clé Cohere disponible
- [ ] Compte Render créé et connecté à GitHub

Après déploiement:

- [ ] Service 1 (actions) déployé et opérationnel
- [ ] Service 2 (rasa) déployé et opérationnel
- [ ] Service 3 (web) déployé
- [ ] Chat widget fonctionne
- [ ] Conversations multilingues OK
- [ ] Feedbacks fonctionnent
- [ ] Sons de notification OK

---

## 🎯 **URLS FINALES**

Une fois déployé, votre chatbot sera accessible sur:

**Site Web Principal:**
- https://expobeton-web.onrender.com

**APIs (pour référence):**
- Action Server: https://expobeton-actions.onrender.com
- Rasa Server: https://expobeton-rasa.onrender.com

---

## 📞 **SUPPORT**

**Documentation Render:**
- https://render.com/docs/docker
- https://render.com/docs/static-sites

**Documentation Rasa:**
- https://rasa.com/docs/rasa-pro/

**Besoin d'aide?**
Vérifiez les logs dans le dashboard Render!
