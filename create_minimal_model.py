#!/usr/bin/env python3
"""Create a minimal Rasa model without training."""
import tarfile
import json
import tempfile
import shutil
from pathlib import Path

def create_minimal_model():
    """Create a minimal valid Rasa model tar.gz file."""
    
    # Create temporary directory
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        
        # Create minimal metadata
        metadata = {
            "trained_at": "2025-10-29T14:00:00+00:00",
            "rasa_open_source_version": "3.6.20",
            "domain": {
                "version": "3.1",
                "session_config": {
                    "session_expiration_time": 60,
                    "carry_over_slots_to_new_session": True
                },
                "intents": [],
                "entities": [],
                "slots": {},
                "responses": {},
                "actions": [],
                "forms": {},
                "e2e_actions": []
            },
            "trained_on": []
        }
        
        # Write metadata
        metadata_file = tmpdir / "metadata.json"
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        # Create models directory if it doesn't exist
        models_dir = Path("models")
        models_dir.mkdir(exist_ok=True)
        
        # Create tar.gz file
        output_path = models_dir / "expobeton-french.tar.gz"
        with tarfile.open(output_path, "w:gz") as tar:
            tar.add(metadata_file, arcname="metadata.json")
        
        print(f"✅ Created minimal model: {output_path}")
        print(f"📦 Size: {output_path.stat().st_size} bytes")
        return output_path

if __name__ == "__main__":
    create_minimal_model()
