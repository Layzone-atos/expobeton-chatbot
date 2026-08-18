#!/usr/bin/env python3
"""Upload updated files to admincb.expobetonrdc.com via FTP"""
import ftplib
import os

FTP_HOST = "ftp.expobetonrdc.com"
FTP_PORT = 21
FTP_USER = "admincb@admincb.expobetonrdc.com"
FTP_PASS = "k!8xt4P96C!%"

LOCAL_DIR = "chatbot-admin"
files_to_upload = ["conversations.php", "conversation_detail.php", "api_chatbot_analytics.php"]

def upload():
    print(f"Connecting to {FTP_HOST}...")
    ftp = ftplib.FTP()
    ftp.connect(FTP_HOST, FTP_PORT)
    ftp.login(FTP_USER, FTP_PASS)
    print(f"Connected. Current dir: {ftp.pwd()}")
    
    # List root to find the right directory
    print("Root contents:")
    ftp.retrlines('LIST')
    
    for filename in files_to_upload:
        local_path = os.path.join(LOCAL_DIR, filename)
        if not os.path.exists(local_path):
            print(f"SKIP: {local_path} not found")
            continue
        
        print(f"\nUploading {filename}...")
        with open(local_path, 'rb') as f:
            ftp.storbinary(f'STOR {filename}', f)
        print(f"OK: {filename} uploaded")
    
    ftp.quit()
    print("\nDone! All files uploaded.")

if __name__ == "__main__":
    upload()
