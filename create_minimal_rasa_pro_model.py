#!/usr/bin/env python3
"""Create a minimal valid Rasa Pro model."""

import tarfile
import json
import tempfile
import os
from pathlib import Path
from datetime import datetime

def create_minimal_model():
    """Create a minimal valid Rasa Pro model."""
    
    print("🔨 Creating minimal Rasa Pro model...")
    
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
        
        # Create minimal NLU data
        nlu_data = {
            "version": "3.1",
            "nlu": [
                {
                    "intent": "greet",
                    "examples": "bonjour\nsalut\nhello\nhi\nBonjour, je m'appelle [Louis Atos](user_name)"
                },
                {
                    "intent": "ask_expobeton",
                    "examples": "c'est quoi expobeton\nqu'est-ce que expo béton\nparle moi d'expobeton\nqu'est-ce que l'expobeton"
                }
            ]
        }
        
        # Create minimal stories
        stories = {
            "version": "3.1",
            "stories": [
                {
                    "story": "greet user",
                    "steps": [
                        {"intent": "greet"},
                        {"action": "utter_greet"}
                    ]
                },
                {
                    "story": "explain expobeton",
                    "steps": [
                        {"intent": "ask_expobeton"},
                        {"action": "utter_expobeton"}
                    ]
                }
            ]
        }
        
        # Create minimal config
        config = {
            "recipe": "default.v1",
            "language": "fr",
            "assistant_id": "upbeat-goal",
            "pipeline": [
                {"name": "WhitespaceTokenizer"},
                {"name": "CountVectorsFeaturizer"}
            ],
            "policies": [
                {"name": "RulePolicy", "core_fallback_threshold": 0.3, "core_fallback_action_name": "action_default_fallback"}
            ]
        }
        
        # Write files
        domain_file = tmpdir / "domain.yml"
        with open(domain_file, 'w', encoding='utf-8') as f:
            json.dump(domain, f, indent=2, ensure_ascii=False)
            
        # Create data directory
        data_dir = tmpdir / "data"
        data_dir.mkdir()
        
        nlu_file = data_dir / "nlu.yml"
        with open(nlu_file, 'w', encoding='utf-8') as f:
            json.dump(nlu_data, f, indent=2, ensure_ascii=False)
            
        stories_file = data_dir / "stories.yml"
        with open(stories_file, 'w', encoding='utf-8') as f:
            json.dump(stories, f, indent=2, ensure_ascii=False)
            
        config_file = tmpdir / "config.yml"
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        
        # Train model using rasa command
        import subprocess
        cmd = [
            "uv", "run", "rasa", "train",
            "--domain", str(domain_file),
            "--data", str(data_dir),
            "--config", str(config_file),
            "--fixed-model-name", "expobeton-french"
        ]
        
        print(f"🚀 Training model with command: {' '.join(cmd)}")
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=os.getcwd())
            
            if result.returncode == 0:
                print("✅ Model trained successfully!")
                print(result.stdout)
                return True
            else:
                print("❌ Training failed!")
                print(result.stderr)
                return False
                
        except Exception as e:
            print(f"❌ Error during training: {e}")
            return False

if __name__ == "__main__":
    if create_minimal_model():
        print("\n🎉 Model created successfully!")
    else:
        print("\n💥 Model creation failed!")