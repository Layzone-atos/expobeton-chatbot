#!/usr/bin/env python3
"""Create a minimal Rasa Pro model manually."""

import tarfile
import json
import tempfile
from pathlib import Path
from datetime import datetime

def create_manual_model():
    """Create a minimal Rasa Pro model manually without training."""
    
    print("🔨 Creating minimal Rasa Pro model manually...")
    
    # Create models directory if it doesn't exist
    models_dir = Path("models")
    models_dir.mkdir(exist_ok=True)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        
        # Create minimal domain
        domain = {
            "version": "3.1",
            "session_config": {
                "session_expiration_time": 60,
                "carry_over_slots_to_new_session": True
            },
            "intents": [
                {"greet": {"use_entities": True}},
                {"ask_expobeton": {"use_entities": True}}
            ],
            "entities": ["user_name"],
            "slots": {
                "user_name": {
                    "type": "text",
                    "mappings": [
                        {
                            "type": "from_text"
                        }
                    ]
                }
            },
            "responses": {
                "utter_greet": [
                    {"text": "Bonjour {{user_name}}! Je suis l'Expert Expo Béton. Comment puis-je vous aider ?"}
                ],
                "utter_expobeton": [
                    {"text": "Expo Béton RDC est un événement majeur dédié au secteur du béton en République Démocratique du Congo. Il présente les dernières innovations, technologies et tendances du secteur."}
                ],
                "utter_default": [
                    {"text": "Désolé, je n'ai pas compris votre message. Pouvez-vous reformuler ?"}
                ]
            },
            "actions": ["utter_greet", "utter_expobeton", "utter_default"],
            "forms": {},
            "e2e_actions": []
        }
        
        # Create minimal metadata
        metadata = {
            "version": "3.1",
            "model_id": "expobeton-french",
            "trained_at": datetime.now().strftime("%Y-%m-%dT%H:%M:%S+00:00"),
            "rasa_open_source_version": "3.10.27",
            "domain": domain,
            "train_schema": {
                "nodes": {},
                "config": {}
            },
            "predict_schema": {
                "nodes": {},
                "config": {}
            },
            "trained_on": []
        }
        
        # Create fingerprint
        fingerprint = {
            "version": "3.10.27",
            "min_compatible_version": "3.10.0",
            "domain": "domain_hash",
            "config": "config_hash",
            "training_data": "training_data_hash"
        }
        
        # Write files
        metadata_file = tmpdir / "metadata.json"
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
            
        fingerprint_file = tmpdir / "fingerprint.json"
        with open(fingerprint_file, 'w', encoding='utf-8') as f:
            json.dump(fingerprint, f, indent=2, ensure_ascii=False)
        
        # Create tar.gz
        output_path = models_dir / "expobeton-french.tar.gz"
        with tarfile.open(output_path, "w:gz") as tar:
            tar.add(metadata_file, arcname="metadata.json")
            tar.add(fingerprint_file, arcname="fingerprint.json")
        
        print(f"✅ Created: {output_path}")
        print(f"📊 Size: {output_path.stat().st_size} bytes")
        return True

if __name__ == "__main__":
    if create_manual_model():
        print("\n🎉 Manual model created successfully!")
        print("\nNext steps:")
        print("1. git add -f models/expobeton-french.tar.gz")
        print("2. git commit -m 'Add manually created minimal Rasa Pro model'")
        print("3. git push origin main")
    else:
        print("\n💥 Manual model creation failed!")