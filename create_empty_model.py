#!/usr/bin/env python3
"""Create a completely empty but valid Rasa model from scratch."""
import tarfile
import json
import tempfile
from pathlib import Path
from datetime import datetime

def create_empty_model():
    """Create a minimal valid Rasa model without any training."""
    
    print("🔨 Creating minimal empty Rasa model...")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        
        # Create minimal domain
        domain = {
            "version": "3.1",
            "session_config": {
                "session_expiration_time": 60,
                "carry_over_slots_to_new_session": True
            },
            "intents": [],
            "entities": [],
            "slots": {},
            "responses": {
                "utter_default": [
                    {"text": "Bonjour! Je suis le chatbot ExpoBeton RDC. Comment puis-je vous aider?"}
                ]
            },
            "actions": [],
            "forms": {},
            "e2e_actions": []
        }
        
        # Create minimal metadata
        metadata = {
            "version": "3.1",
            "model_id": "expobeton-french",
            "trained_at": datetime.now().strftime("%Y-%m-%dT%H:%M:%S+00:00"),
            "rasa_open_source_version": "3.6.20",
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
        
        # Write metadata
        metadata_file = tmpdir / "metadata.json"
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        
        # Create empty fingerprint
        fingerprint_file = tmpdir / "fingerprint.json"
        with open(fingerprint_file, 'w', encoding='utf-8') as f:
            json.dump({}, f)
        
        # Create models directory
        models_dir = Path("models")
        models_dir.mkdir(exist_ok=True)
        
        # Create tar.gz
        output_path = models_dir / "expobeton-french.tar.gz"
        print("📦 Packaging model...")
        with tarfile.open(output_path, "w:gz") as tar:
            tar.add(metadata_file, arcname="metadata.json")
            tar.add(fingerprint_file, arcname="fingerprint.json")
        
        print(f"✅ Empty model created: {output_path}")
        print(f"📊 Size: {output_path.stat().st_size} bytes")
        print("\n🎉 Model ready for deployment!")
        return output_path

if __name__ == "__main__":
    create_empty_model()
