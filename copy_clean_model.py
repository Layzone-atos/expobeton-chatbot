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
            # Keep version
            domain["intents"] = []
            domain["entities"] = []
            domain["slots"] = {}
            domain["actions"] = []
            domain["forms"] = {}
            domain["e2e_actions"] = []
            domain["responses"] = {
                "utter_default": [
                    {"text": "Bonjour! Je suis le chatbot ExpoBeton RDC."}
                ]
            }
        
        # Save simplified metadata
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        
        # Repackage
        with tarfile.open(target, "w:gz") as tar:
            for item in tmpdir.iterdir():
                tar.add(item, arcname=item.name)
        
        print(f"✅ Created: {target}")
        print(f"📊 Size: {target.stat().st_size} bytes")

if __name__ == "__main__":
    copy_and_clean_model()
