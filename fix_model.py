#!/usr/bin/env python3
"""Extract, fix, and repackage Rasa model to remove invalid slot mappings."""
import tarfile
import json
import tempfile
import shutil
from pathlib import Path

def fix_slot_mappings(domain):
    """Fix invalid slot mappings in domain."""
    if "slots" not in domain:
        return domain
    
    for slot_name, slot_config in domain["slots"].items():
        if "mappings" in slot_config:
            # Ensure mappings is a list
            if slot_config["mappings"] is None:
                slot_config["mappings"] = []
            for mapping in slot_config["mappings"]:
                # Replace invalid mapping types with 'custom'
                if mapping.get("type") in ["from_llm", "controlled"]:
                    print(f"  ✅ Fixed slot '{slot_name}': {mapping['type']} → custom")
                    mapping["type"] = "custom"
    
    # Ensure all required domain fields are lists, not None
    for field in ["intents", "entities", "actions", "forms", "e2e_actions"]:
        if field in domain and domain[field] is None:
            print(f"  ✅ Fixed domain field '{field}': None → []")
            domain[field] = []
    
    return domain

def fix_model():
    """Extract model, fix domain, and repackage."""
    
    source_model = Path("models/expobeton-fallback.tar.gz")
    target_model = Path("models/expobeton-french.tar.gz")
    
    if not source_model.exists():
        print(f"❌ Source model not found: {source_model}")
        return False
    
    print(f"🔧 Fixing model: {source_model}")
    
    # Create temporary directory
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        extract_dir = tmpdir / "model"
        extract_dir.mkdir()
        
        # Extract model
        print("📦 Extracting model...")
        with tarfile.open(source_model, "r:gz") as tar:
            tar.extractall(extract_dir)
        
        # Find and fix metadata.json
        metadata_file = extract_dir / "metadata.json"
        if metadata_file.exists():
            print("🔍 Loading metadata...")
            with open(metadata_file, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
            
            # Fix domain in metadata
            if "domain" in metadata:
                print("🛠️  Fixing slot mappings...")
                metadata["domain"] = fix_slot_mappings(metadata["domain"])
                
                # Write back metadata
                print("💾 Saving fixed metadata...")
                with open(metadata_file, 'w', encoding='utf-8') as f:
                    json.dump(metadata, f, indent=2, ensure_ascii=False)
        
        # Repackage model
        print("📦 Repackaging model...")
        with tarfile.open(target_model, "w:gz") as tar:
            for item in extract_dir.iterdir():
                tar.add(item, arcname=item.name)
        
        print(f"✅ Fixed model saved: {target_model}")
        print(f"📊 Size: {target_model.stat().st_size} bytes")
        return True

if __name__ == "__main__":
    if fix_model():
        print("\n🎉 Model fixed successfully!")
        print("\nNext steps:")
        print("1. git add -f models/expobeton-french.tar.gz")
        print("2. git commit -m 'Fix invalid slot mappings in model'")
        print("3. git push origin main")
    else:
        print("\n❌ Model fix failed!")
