#!/usr/bin/env python3
"""
Script to train a new Rasa model
"""
import os
import subprocess
import sys

def train_model():
    """Train a new Rasa model"""
    print("Training new Rasa model...")
    
    # Change to the project directory
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    # Run the training command
    try:
        result = subprocess.run([
            "rasa", "train",
            "--fixed-model-name", "expobeton-french",
            "--out", "models/"
        ], check=True, capture_output=True, text=True)
        
        print("Training completed successfully!")
        print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Training failed with error: {e}")
        print(f"Error output: {e.stderr}")
        return False

if __name__ == "__main__":
    success = train_model()
    sys.exit(0 if success else 1)