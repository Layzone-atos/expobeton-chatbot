#!/usr/bin/env python3
"""Train a minimal Rasa Pro model."""

import subprocess
import os
import sys

def train_model():
    """Train a minimal model with Rasa Pro."""
    
    # Set environment variables
    os.environ['RASA_LICENSE'] = 'eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJqdGkiOiIwODk0MDJjOS00NDIyLTQ5MzktYjc5OC0zYjdmMWEwM2MzNmUiLCJpYXQiOjE3NjEzOTY1MDIsIm5iZiI6MTc2MTM5NjUwMCwic2NvcGUiOiJyYXNhOnBybyByYXNhOnBybzpjaGFtcGlvbiByYXNhOnZvaWNlIiwiZXhwIjoxODU2MDkwOTAwLCJlbWFpbCI6ImJvdEBleHBvYmV0b25yZGMuY29tIiwiY29tcGFueSI6IlJhc2EgQ2hhbXBpb25zIn0.yMrH3Z4cMDR13sj79yqiVhUohkRqgfE4iwYt81-vJlzGEy-KRE7bSuvMP5_mX5aBSF0Mtl_a0g8D2wfiKUA8o_4Q92Hvd7jB393GdS1bzs2gr0b44IgHm2sxXP3QzWtOI_iXGqdI-N_7vu1zpcfK8ig_nKYGMFqJ4LT9rnAeFU9OjwV70LReStA-kQ7Oo_TypRb_vzOXE647rxmFDO1OeTxR_1nYaBgdV-FsWP8_MNkX8dYNDtVwgP1cebZGYfvKbo0yneU1xhLbl4ztumMjcNzjC_ptr1HQ-nXJdvSSwJifpkhD_8ukYxWPFeG7tYJrayON6VtpxpPgKTFdEb67PQ'
    
    # Train command
    cmd = [
        'uv', 'run', 'rasa', 'train',
        '--domain', 'domain_simple.yml',
        '--data', 'data_simple',
        '--config', 'config_simple.yml',
        '--fixed-model-name', 'expobeton-french'
    ]
    
    print("🚀 Training minimal Rasa Pro model...")
    print(f"Command: {' '.join(cmd)}")
    
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
    if train_model():
        print("\n🎉 Next steps:")
        print("1. git add -f models/expobeton-french.tar.gz")
        print("2. git commit -m 'Add newly trained minimal Rasa Pro model'")
        print("3. git push origin main")
    else:
        print("\n💥 Model training failed!")
        sys.exit(1)