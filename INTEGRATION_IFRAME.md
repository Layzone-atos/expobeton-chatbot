# 🤖 Intégration du Chatbot ExpoBeton via iframe

## 📦 URL de votre chatbot déployé
```
https://web-production-9f398e.up.railway.app
```

## 🚀 Code d'intégration (Copier-Coller)

### Option 1: Intégration simple (Recommandé)
Ajoutez ce code **avant la balise `</body>`** de votre site web:

```html
<!-- ExpoBeton Chatbot -->
<iframe 
    src="https://web-production-9f398e.up.railway.app/web/chatbot-embed.html"
    style="position:fixed;bottom:0;right:0;width:100%;height:100%;border:none;pointer-events:auto;z-index:999999"
    title="ExpoBeton Assistant"
></iframe>
```

### Option 2: Intégration avec ID (Pour contrôle JavaScript)
```html
<!-- ExpoBeton Chatbot -->
<iframe 
    id="expobeton-chatbot"
    src="https://web-production-9f398e.up.railway.app/web/chatbot-embed.html"
    style="position:fixed;bottom:0;right:0;width:100%;height:100%;border:none;pointer-events:auto;z-index:999999"
    title="ExpoBeton Assistant"
></iframe>
```

### Option 3: Intégration WordPress (Widget HTML personnalisé)
1. Allez dans **Apparence > Widgets**
2. Ajoutez un widget **HTML personnalisé** dans le pied de page
3. Collez le code de l'Option 1

### Option 4: Intégration via Google Tag Manager
1. Créez une nouvelle balise **HTML personnalisé**
2. Collez le code de l'Option 1
3. Déclencheur: **Toutes les pages**

## 📋 Pages de test disponibles

| Page | URL | Description |
|------|-----|-------------|
| **Chatbot intégré** | https://web-production-9f398e.up.railway.app/web/chatbot-embed.html | Version iframe pure |
| **Page de démo** | https://web-production-9f398e.up.railway.app/web/index.html | Démo complète avec contenu |
| **Documentation** | https://web-production-9f398e.up.railway.app/web/embed-example.html | Instructions d'intégration |

## ✅ Vérification

Pour tester que tout fonctionne:

1. **Testez directement l'iframe:**
   ```
   https://web-production-9f398e.up.railway.app/web/chatbot-embed.html
   ```
   Vous devriez voir le bouton de chat en bas à droite.

2. **Testez sur votre site:**
   - Intégrez le code iframe
   - Ouvrez votre site dans un navigateur
   - Le bouton de chat doit apparaître en bas à droite
   - Cliquez dessus pour tester une conversation

## 🎨 Personnalisation de la position

### Positionner à gauche
```html
<iframe 
    src="https://web-production-9f398e.up.railway.app/web/chatbot-embed.html"
    style="position:fixed;bottom:0;left:0;width:100%;height:100%;border:none;pointer-events:auto;z-index:999999"
    title="ExpoBeton Assistant"
></iframe>
```

### Ajuster pour mobile
```html
<style>
    @media (max-width: 768px) {
        #expobeton-chatbot {
            width: 100% !important;
        }
    }
</style>
```

## 🔧 Fonctionnalités incluses

✅ Bouton flottant en bas à droite  
✅ Formulaire de collecte d'informations (nom, téléphone, email)  
✅ Support multilingue (FR, EN, SW)  
✅ Informations sur Expo Béton RDC 2026 à Kalemie  
✅ Responsive (mobile + desktop)  
✅ Bouton "Terminer la conversation"  
✅ Envoi par email des conversations  

## 📊 Questions de test suggérées

Après intégration, testez avec ces questions:

### En Français:
- "Quand aura lieu l'Expo Béton 2026 ?"
- "Où se tiendra l'événement ?"
- "Pourquoi Kalemie ?"
- "Comment participer ?"
- "Quels sont les tarifs ?"

### En Anglais:
- "When is the Expo Béton 2026?"
- "Where will it take place?"
- "Why Kalemie?"
- "How to participate?"

### En Swahili:
- "Expo itakuwa lini?"
- "Itafanyika wapi?"

## 🛠️ Dépannage

### Le chatbot ne s'affiche pas
- Vérifiez que l'URL est correcte
- Vérifiez la console du navigateur (F12)
- Assurez-vous que le z-index est suffisamment élevé

### Le chatbot s'affiche mais ne répond pas
- Vérifiez que le service RASA est actif sur Railway
- Testez directement: https://web-production-9f398e.up.railway.app/webhooks/rest/webhook

### Problème de CORS
- Le chatbot est configuré pour accepter les requêtes cross-origin
- Si problème persistant, contactez le support

## 📞 Support

Pour toute question ou problème d'intégration, référez-vous à la documentation complète:
```
https://web-production-9f398e.up.railway.app/web/embed-example.html
```

---

**Dernière mise à jour:** 3 décembre 2025  
**Version du chatbot:** Expo Béton RDC 2026 - Kalemie Edition
