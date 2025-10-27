"""
Script de test pour vérifier l'envoi d'emails de conversation
"""

import os
import sys
from datetime import datetime
from pathlib import Path

# Ajouter le projet au path
sys.path.insert(0, str(Path(__file__).parent))

# Charger les variables d'environnement
from dotenv import load_dotenv
load_dotenv()

# Import de la fonction d'envoi d'email
from actions.actions import send_conversation_email

# Données de test
test_session_id = "test_session_123"
test_user_info = {
    "name": "Test Utilisateur",
    "phone": "+243 123 456 789",
    "email": "test@example.com"
}

test_messages = [
    {
        "sender": "user",
        "text": "Bonjour, c'est quoi ExpoBeton?",
        "timestamp": datetime.now()
    },
    {
        "sender": "bot",
        "text": "ExpoBeton RDC est le salon international de la construction...",
        "timestamp": datetime.now()
    },
    {
        "sender": "user",
        "text": "Quelles sont les dates?",
        "timestamp": datetime.now()
    },
    {
        "sender": "bot",
        "text": "La 10ème édition s'est déroulée du 8 au 11 Octobre 2025.",
        "timestamp": datetime.now()
    }
]

print("="*60)
print("TEST D'ENVOI D'EMAIL DE CONVERSATION")
print("="*60)
print()

# Vérifier les variables d'environnement
print("📋 Configuration SMTP:")
print(f"   SMTP_SERVER: {os.getenv('SMTP_SERVER')}")
print(f"   SMTP_PORT: {os.getenv('SMTP_PORT')}")
print(f"   SMTP_USERNAME: {os.getenv('SMTP_USERNAME')}")
print(f"   SMTP_PASSWORD: {'***' if os.getenv('SMTP_PASSWORD') else 'NOT SET'}")
print(f"   NOTIFICATION_EMAIL: bot@expobetonrdc.com")
print()

# Tester l'envoi d'email
print("📧 Tentative d'envoi d'email...")
print()

try:
    send_conversation_email(test_session_id, test_user_info, test_messages)
    print()
    print("✅ Test terminé! Vérifiez les logs ci-dessus.")
    print()
    print("📬 Si vous voyez '[SUCCESS]', l'email a été envoyé!")
    print("📬 Vérifiez votre boîte mail: bot@expobetonrdc.com")
except Exception as e:
    print()
    print(f"❌ Erreur lors du test: {e}")
    import traceback
    traceback.print_exc()

print()
print("="*60)
