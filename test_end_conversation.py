"""
Test script to verify /end_conversation endpoint
"""

import requests
import json
from datetime import datetime

# Test data
test_data = {
    "sender": "test_user_123",
    "message": "/end_conversation",
    "metadata": {
        "messages": [
            {
                "sender": "user",
                "text": "Bonjour",
                "timestamp": datetime.now().isoformat()
            },
            {
                "sender": "bot",
                "text": "Bonjour! Comment puis-je vous aider?",
                "timestamp": datetime.now().isoformat()
            },
            {
                "sender": "user",
                "text": "C'est quoi ExpoBeton?",
                "timestamp": datetime.now().isoformat()
            },
            {
                "sender": "bot",
                "text": "ExpoBeton RDC est le salon international...",
                "timestamp": datetime.now().isoformat()
            }
        ],
        "user_info": {
            "name": "Louison Atundu TEST",
            "phone": "+243 123 456 789",
            "email": "louison@test.com"
        },
        "session_id": "test_session_manual",
        "ended_at": datetime.now().isoformat(),
        "total_messages": 4
    }
}

print("="*80)
print("TESTING /end_conversation ENDPOINT")
print("="*80)
print()

print("📤 Sending request to: http://localhost:5005/webhooks/rest/webhook")
print()
print("📦 Payload:")
print(json.dumps(test_data, indent=2))
print()

try:
    response = requests.post(
        'http://localhost:5005/webhooks/rest/webhook',
        json=test_data,
        headers={'Content-Type': 'application/json'}
    )
    
    print(f"📥 Response Status: {response.status_code}")
    print()
    
    if response.ok:
        print("✅ SUCCESS! Response:")
        print(json.dumps(response.json(), indent=2))
    else:
        print(f"❌ FAILED! Status: {response.status_code}")
        print(f"Response: {response.text}")
    
except Exception as e:
    print(f"❌ ERROR: {e}")
    import traceback
    traceback.print_exc()

print()
print("="*80)
print("Check the action server logs above for [ACTION END CONVERSATION] messages")
print("Check your email at bot@expobetonrdc.com")
print("="*80)
