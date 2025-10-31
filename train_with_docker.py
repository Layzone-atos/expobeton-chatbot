#!/usr/bin/env python3
"""Train model with Docker for Rasa Pro 3.10.27 compatibility."""

import subprocess
import os
import sys
from pathlib import Path

def train_with_docker():
    """Train model using Docker to ensure version compatibility."""
    
    print("🐳 Training model with Docker (Rasa Pro 3.10.27)...")
    
    # Get current directory
    current_dir = Path.cwd()
    
    # Set environment variables
    env = os.environ.copy()
    env['RASA_LICENSE'] = 'eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJqdGkiOiIwODk0MDJjOS00NDIyLTQ5MzktYjc5OC0zYjdmMWEwM2MzNmUiLCJpYXQiOjE3NjEzOTY1MDIsIm5iZiI6MTc2MTM5NjUwMCwic2NvcGUiOiJyYXNhOnBybyByYXNhOnBybzpjaGFtcGlvbiByYXNhOnZvaWNlIiwiZXhwIjoxODU2MDkwOTAwLCJlbWFpbCI6ImJvdEBleHBvYmV0b25yZGMuY29tIiwiY29tcGFueSI6IlJhc2EgQ2hhbXBpb25zIn0.yMrH3Z4cMDR13sj79yqiVhUohkRqgfE4iwYt81-vJlzGEy-KRE7bSuvMP5_mX5aBSF0Mtl_a0g8D2wfiKUA8o_4Q92Hvd7jB393GdS1bzs2gr0b44IgHm2sxXP3QzWtOI_iXGqdI-N_7vu1zpcfK8ig_nKYGMFqJ4LT9rnAeFU9OjwV70LReStA-kQ7Oo_TypRb_vzOXE647rxmFDO1OeTxR_1nYaBgdV-FsWP8_MNkX8dYNDtVwgP1cebZGYfvKbo0yneU1xhLbl4ztumMjcNzjC_ptr1HQ-nXJdvSSwJifpkhD_8ukYxWPFeG7tYJrayON6VtpxpPgKTFdEb67PQ'
    env['RASA_PRO_LICENSE'] = 'eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJqdGkiOiIwODk0MDJjOS00NDIyLTQ5MzktYjc5OC0zYjdmMWEwM2MzNmUiLCJpYXQiOjE3NjEzOTY1MDIsIm5iZiI6MTc2MTM5NjUwMCwic2NvcGUiOiJyYXNhOnBybyByYXNhOnBybzpjaGFtcGlvbiByYXNhOnZvaWNlIiwiZXhwIjoxODU2MDkwOTAwLCJlbWFpbCI6ImJvdEBleHBvYmV0b25yZGMuY29tIiwiY29tcGFueSI6IlJhc2EgQ2hhbXBpb25zIn0.yMrH3Z4cMDR13sj79yqiVhUohkRqgfE4iwYt81-vJlzGEy-KRE7bSuvMP5_mX5aBSF0Mtl_a0g8D2wfiKUA8o_4Q92Hvd7jB393GdS1bzs2gr0b44IgHm2sxXP3QzWtOI_iXGqdI-N_7vu1zpcfK8ig_nKYGMFqJ4LT9rnAeFU9OjwV70LReStA-kQ7Oo_TypRb_vzOXE647rxmFDO1OeTxR_1nYaBgdV-FsWP8_MNkX8dYNDtVwgP1cebZGYfvKbo0yneU1xhLbl4ztumMjcNzjC_ptr1HQ-nXJdvSSwJifpkhD_8ukYxWPFeG7tYJrayON6VtpxpPgKTFdEb67PQ'
    
    # Docker command
    cmd = [
        'docker', 'run', 
        '-v', f'{current_dir}:/app',
        '-e', 'RASA_LICENSE',
        '-e', 'RASA_PRO_LICENSE',
        'europe-west3-docker.pkg.dev/rasa-releases/rasa-pro/rasa-pro:3.10.27',
        'train',
        '--domain', 'domain_simple.yml',
        '--data', 'data_simple',
        '--config', 'config_simple.yml',
        '--fixed-model-name', 'expobeton-french',
        '--out', 'models'
    ]
    
    print(f"🚀 Running: {' '.join(cmd)}")
    
    try:
        # Run Docker command
        result = subprocess.run(cmd, env=env, capture_output=True, text=True, cwd=current_dir)
        
        if result.returncode == 0:
            print("✅ Model trained successfully with Docker!")
            print(result.stdout)
            return True
        else:
            print("❌ Docker training failed!")
            print(result.stderr)
            return False
            
    except Exception as e:
        print(f"❌ Error during Docker training: {e}")
        return False

if __name__ == "__main__":
    if train_with_docker():
        print("\n🎉 Next steps:")
        print("1. git add -f models/expobeton-french.tar.gz")
        print("2. git commit -m 'Add Docker-trained Rasa Pro 3.10.27 model'")
        print("3. git push origin main")
    else:
        print("\n💥 Docker training failed!")
        sys.exit(1)