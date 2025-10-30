#!/usr/bin/env python3
"""Copy and clean a working model's structure."""
import tarfile
import json
import tempfile
from pathlib import Path

def copy_and_clean_model():
    """Copy a working model and remove all complex fields."""
    
    source = Path("models/20251025-130456-pizzicato-peach.tar.gz")
    target = Path("models/expobeton-french.tar.gz")
    
    print(f"📦 Copying from: {source.name}")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        
        # Extract source
        with tarfile.open(source, "r:gz") as tar:
            tar.extractall(tmpdir)
        
        # Load and simplify metadata
        metadata_file = tmpdir / "metadata.json"
        with open(metadata_file, 'r', encoding='utf-8') as f:
            metadata = json.load(f)
        
        # Keep ONLY the structure, remove all content
        if "domain" in metadata:
            domain = metadata["domain"]
            # Add minimal working intents and responses
            domain["intents"] = [
                {"greet": {"use_entities": []}},
                {"nlu_fallback": {"use_entities": []}}
            ]
            domain["entities"] = []
            domain["slots"] = {}
            domain["actions"] = ["utter_greet", "utter_default"]
            domain["forms"] = {}
            domain["e2e_actions"] = []
            domain["responses"] = {
                "utter_greet": [
                    {"text": "Bonjour! Je suis le chatbot ExpoBeton RDC. Comment puis-je vous aider?"}
                ],
                "utter_default": [
                    {"text": "Bonjour! Je suis le chatbot ExpoBeton RDC. Comment puis-je vous aider?"}
                ]
            }
        
        # Clear train_schema and predict_schema to remove Rasa Pro components
        if "train_schema" in metadata:
            metadata["train_schema"] = {"nodes": {}, "config": {}}
        if "predict_schema" in metadata:
            metadata["predict_schema"] = {"nodes": {}, "config": {}}
        
        # Save simplified metadata
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        
        # Create minimal rules.yml
        rules_file = tmpdir / "rules.yml"
        with open(rules_file, 'w', encoding='utf-8') as f:
            f.write("""version: \"3.1\"

rules:
  - rule: Greet user
    steps:
      - intent: greet
      - action: utter_greet

  - rule: Default fallback
    steps:
      - intent: nlu_fallback
      - action: utter_default
""")
        
        # Repackage
        with tarfile.open(target, "w:gz") as tar:
            for item in tmpdir.iterdir():
                tar.add(item, arcname=item.name)
            
            # Add rules.yml if it exists
            if rules_file.exists():
                tar.add(rules_file, arcname="data/rules.yml")
        
        print(f"✅ Created: {target}")
        print(f"📊 Size: {target.stat().st_size} bytes")

if __name__ == "__main__":
    copy_and_clean_model()
