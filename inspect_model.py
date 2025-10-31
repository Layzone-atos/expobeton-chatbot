#!/usr/bin/env python3
"""Inspect model to find None fields."""
import tarfile
import json
from pathlib import Path

def inspect_model():
    """Extract and inspect model metadata."""
    
    source_model = Path("models/expobeton-fallback.tar.gz")
    
    if not source_model.exists():
        print(f"❌ Model not found: {source_model}")
        return
    
    print(f"🔍 Inspecting model: {source_model}\n")
    
    # Extract and read metadata
    with tarfile.open(source_model, "r:gz") as tar:
        metadata_member = tar.getmember("metadata.json")
        metadata_file = tar.extractfile(metadata_member)
        metadata = json.load(metadata_file)
    
    # Check domain for None values
    domain = metadata.get("domain", {})
    
    print("📊 Domain structure:\n")
    
    def check_none(obj, path=""):
        """Recursively check for None values."""
        if isinstance(obj, dict):
            for key, value in obj.items():
                new_path = f"{path}.{key}" if path else key
                if value is None:
                    print(f"  ❌ {new_path} = None")
                elif isinstance(value, (dict, list)):
                    check_none(value, new_path)
                else:
                    print(f"  ✅ {new_path} = {type(value).__name__}")
        elif isinstance(obj, list):
            if len(obj) == 0:
                print(f"  ✅ {path} = [] (empty list)")
            else:
                for i, item in enumerate(obj):
                    check_none(item, f"{path}[{i}]")
    
    check_none(domain)
    
    print("\n📋 Full domain keys:")
    print(json.dumps(list(domain.keys()), indent=2))

if __name__ == "__main__":
    inspect_model()
