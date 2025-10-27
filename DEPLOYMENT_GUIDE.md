# 🚀 Guide de Déploiement - ExpoBeton RDC Chatbot
## Hébergement Partagé + PythonAnywhere

---

## 📋 TABLE DES MATIÈRES

1. [Vue d'ensemble](#vue-densemble)
2. [Partie 1: Backend sur PythonAnywhere](#partie-1-backend-sur-pythonanywhere)
3. [Partie 2: Widget sur serveur mutualisé](#partie-2-widget-sur-serveur-mutualisé)
4. [Vérification et tests](#vérification-et-tests)
5. [Dépannage](#dépannage)

---

## 🎯 VUE D'ENSEMBLE

### Architecture

```
┌─────────────────────────────────────┐
│  expobetonrdc.com                   │
│  (Hébergement Partagé)              │
│  ├── Site principal                 │
│  └── /chat/chat-widget-standalone.js│
└──────────────┬──────────────────────┘
               │
               │ Appelle API via HTTPS
               ▼
┌─────────────────────────────────────┐
│  VOTRE_USERNAME.pythonanywhere.com  │
│  (Backend Gratuit)                  │
│  ├── Flask API                      │
│  ├── Rasa Server                    │
│  └── Action Server                  │
└─────────────────────────────────────┘
```

### Ce dont vous avez besoin

- ✅ Compte PythonAnywhere (gratuit)
- ✅ Accès FTP/cPanel à votre hébergement mutualisé
- ✅ Les fichiers de ce projet

---

## 📦 PARTIE 1: BACKEND SUR PYTHONANYWHERE

### Étape 1: Créer le compte

1. Allez sur https://www.pythonanywhere.com
2. Cliquez **"Start running Python online"**
3. Créez un compte **Beginner** (gratuit)
4. Notez votre **USERNAME** (important!)

---

### Étape 2: Uploader les fichiers

#### Via l'interface Web

1. Cliquez **"Files"** dans le menu
2. Créez un dossier `expobeton-bot`
3. Uploadez **TOUS** ces fichiers/dossiers:

```
expobeton-bot/
├── actions/
│   ├── __init__.py
│   ├── actions.py
│   └── action_human_handoff.py
├── domain/
│   └── ... (tous les fichiers domain)
├── data/
│   └── ... (tous les fichiers data)
├── models/
│   └── expobeton-french.tar.gz
├── .env
├── flask_app.py
├── config.yml
├── endpoints.yml
└── pyproject.toml
```

**IMPORTANT:** N'uploadez PAS le dossier `.venv` (trop lourd)

---

### Étape 3: Installer les dépendances

1. Cliquez **"Consoles"** → **"Bash"**
2. Exécutez ces commandes:

```bash
cd expobeton-bot

# Installer UV
curl -LsSf https://astral.sh/uv/install.sh | sh
source ~/.bashrc

# Installer les dépendances
uv sync

# Installer Flask-CORS manuellement si nécessaire
pip install flask-cors

# Vérifier
python -c "import flask; print('Flask OK')"
python -c "import rasa; print('Rasa OK')"
```

---

### Étape 4: Configurer la Web App

1. Cliquez **"Web"** dans le menu
2. **"Add a new web app"**
3. Choisissez votre domaine: `VOTRE_USERNAME.pythonanywhere.com`
4. **"Manual configuration"** (PAS Flask!)
5. Choisissez **Python 3.10**

---

### Étape 5: Configurer WSGI

1. Dans la page Web app, section **"Code"**
2. Cliquez sur le lien **WSGI configuration file**
3. **SUPPRIMEZ TOUT** le contenu
4. **REMPLACEZ** par:

```python
import sys
import os

# IMPORTANT: Remplacez VOTRE_USERNAME par votre vrai username!
project_home = '/home/VOTRE_USERNAME/expobeton-bot'

if project_home not in sys.path:
    sys.path = [project_home] + sys.path

# Charger les variables d'environnement
os.chdir(project_home)

# Importer l'application Flask
from flask_app import app as application
```

5. **Sauvegardez** (Ctrl+S)

---

### Étape 6: Configurer le Virtualenv

1. Dans la page Web app, section **"Virtualenv"**
2. Entrez le chemin: `/home/VOTRE_USERNAME/expobeton-bot/.venv`
3. Cliquez sur le ✓

---

### Étape 7: Démarrer l'application

1. En haut de la page, cliquez le gros bouton vert **"Reload"**
2. Attendez quelques secondes
3. Visitez: `https://VOTRE_USERNAME.pythonanywhere.com`
4. Vous devriez voir:

```json
{
  "status": "online",
  "service": "ExpoBeton RDC Chatbot API",
  "version": "1.0.0",
  "agent_loaded": true
}
```

✅ **Si vous voyez ça, le backend fonctionne!**

---

## 🌐 PARTIE 2: WIDGET SUR SERVEUR MUTUALISÉ

### Étape 1: Modifier l'URL du backend

1. Ouvrez le fichier `web/chat-widget-standalone.js`
2. Ligne 16, remplacez:

```javascript
const RASA_SERVER_URL = 'https://VOTRE_USERNAME.pythonanywhere.com';
```

**IMPORTANT:** Remplacez `VOTRE_USERNAME` par votre vrai username PythonAnywhere!

---

### Étape 2: Uploader sur votre serveur

#### Via FTP (FileZilla, etc.)

1. Connectez-vous à votre FTP
2. Allez dans `public_html/` (ou `www/` selon hébergeur)
3. Créez un dossier `chat/`
4. Uploadez ces 2 fichiers:
   - `chat-widget-standalone.js`
   - `index-demo.html` (optionnel, pour tester)

#### Via cPanel File Manager

1. Connectez-vous à cPanel
2. Ouvrez **"Gestionnaire de fichiers"**
3. Allez dans `public_html/`
4. Cliquez **"Nouveau dossier"** → `chat`
5. Uploadez les fichiers

---

### Étape 3: Tester le widget

Visitez: `https://expobetonrdc.com/chat/index-demo.html`

Vous devriez voir:
- ✅ Le bouton flottant 💬 en bas à droite
- ✅ Cliquez dessus → formulaire s'ouvre
- ✅ Remplissez le formulaire → chat démarre
- ✅ Envoyez un message → réponse du bot!

---

### Étape 4: Intégrer sur votre site

#### Sur une page HTML statique

Ajoutez avant `</body>`:

```html
<!-- ExpoBeton Chatbot -->
<script src="https://expobetonrdc.com/chat/chat-widget-standalone.js"></script>
```

#### Sur WordPress

**Méthode 1: Via un plugin**

1. Installez le plugin **"Insert Headers and Footers"**
2. Allez dans **Réglages → Insert Headers and Footers**
3. Dans la section **"Scripts in Footer"**, ajoutez:

```html
<script src="<?php echo home_url('/chat/chat-widget-standalone.js'); ?>"></script>
```

**Méthode 2: Via le thème**

1. Allez dans **Apparence → Éditeur de thème**
2. Ouvrez **footer.php**
3. Trouvez `<?php wp_footer(); ?>`
4. Ajoutez AVANT:

```html
<!-- ExpoBeton Chatbot -->
<script src="<?php echo home_url('/chat/chat-widget-standalone.js'); ?>"></script>
```

---

## ✅ VÉRIFICATION ET TESTS

### Checklist Backend (PythonAnywhere)

- [ ] Le site `https://VOTRE_USERNAME.pythonanywhere.com` affiche le JSON
- [ ] Le JSON montre `"agent_loaded": true`
- [ ] Pas d'erreurs dans les logs (Web → Log files)

### Checklist Widget

- [ ] Le fichier est accessible: `https://expobetonrdc.com/chat/chat-widget-standalone.js`
- [ ] Le bouton 💬 apparaît en bas à droite
- [ ] Le formulaire s'ouvre au clic
- [ ] Les messages sont envoyés et les réponses arrivent
- [ ] Le bouton "Terminer la conversation" fonctionne

### Tester une conversation complète

1. Ouvrez votre site
2. Cliquez sur le bouton 💬
3. Remplissez: Nom, Téléphone, Email
4. Cliquez **"Commencer la discussion"**
5. Envoyez: "C'est quoi ExpoBeton?"
6. Vérifiez la réponse du bot
7. Envoyez: "Merci"
8. Cliquez **"Terminer la conversation"**
9. Vérifiez l'email à **bot@expobetonrdc.com**

---

## 🔧 DÉPANNAGE

### Problème: Le backend ne démarre pas

**Solution:**

1. Vérifiez les logs: Web → Log files → Error log
2. Erreur commune: `Module not found`
   ```bash
   cd expobeton-bot
   pip install <module_manquant>
   ```

### Problème: "agent_loaded": false

**Solution:**

1. Vérifiez que le fichier `models/expobeton-french.tar.gz` existe
2. Vérifiez les permissions:
   ```bash
   chmod -R 755 /home/VOTRE_USERNAME/expobeton-bot
   ```

### Problème: CORS error dans le navigateur

**Solution:**

1. Vérifiez que `flask-cors` est installé:
   ```bash
   pip install flask-cors
   ```

2. Ajoutez dans PythonAnywhere Web → **"Force HTTPS"** = **Yes**

### Problème: Le bouton n'apparaît pas

**Solution:**

1. Ouvrez la console du navigateur (F12)
2. Vérifiez les erreurs JavaScript
3. Vérifiez l'URL du script:
   ```html
   <script src="https://expobetonrdc.com/chat/chat-widget-standalone.js"></script>
   ```

### Problème: Les messages ne s'envoient pas

**Solution:**

1. Ouvrez la console (F12) → Network
2. Vérifiez l'URL appelée: `https://VOTRE_USERNAME.pythonanywhere.com/webhooks/rest/webhook`
3. Statut 500? → Vérifiez les logs PythonAnywhere
4. Statut 404? → Vérifiez l'URL dans `chat-widget-standalone.js`

---

## 📧 EMAILS

Les emails de conversation sont envoyés automatiquement à **bot@expobetonrdc.com** quand:
- L'utilisateur clique "Terminer la conversation"
- L'utilisateur est inactif 10+ minutes
- L'utilisateur dit "au revoir"

Configuration SMTP dans `.env`:
```env
SMTP_SERVER=mail.expobetonrdc.com
SMTP_PORT=587
SMTP_USERNAME=bot@expobetonrdc.com
SMTP_PASSWORD=~UrHWZVkUds7
```

---

## 💰 COÛTS

- **PythonAnywhere Free:** 0€ (suffisant pour démarrer)
- **PythonAnywhere Hacker:** 5$/mois (si vous avez beaucoup de trafic)
- **Hébergement mutualisé:** Déjà payé ✅

---

## 🎉 FÉLICITATIONS!

Votre chatbot ExpoBeton RDC est maintenant en ligne! 🚀

### Prochaines étapes

1. Testez sur mobile et desktop
2. Intégrez sur toutes vos pages
3. Surveillez les emails de conversations
4. Améliorez les réponses du bot si nécessaire

---

## 📞 SUPPORT

Pour toute question sur:
- **PythonAnywhere:** https://help.pythonanywhere.com
- **Ce chatbot:** Consultez la documentation dans le dossier du projet

---

**Bonne chance! 🏗️🇨🇩**
