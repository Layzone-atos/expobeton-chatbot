import ftplib
import os

FTP_HOST = "ftp.expobetonrdc.com"
FTP_USER = "admincb@admincb.expobetonrdc.com"
FTP_PASS = "k!8xt4P96C!%"
LOCAL_DIR = "chatbot-admin"

files_to_upload = [
    "config.php",
    "conversations.php",
    "conversation_detail.php",
    "api_chatbot_analytics.php"
]

print(f"Connecting to {FTP_HOST}...")
ftp = ftplib.FTP(FTP_HOST)
ftp.login(FTP_USER, FTP_PASS)
ftp.encoding = "utf-8"
print(f"Connected. Current dir: {ftp.pwd()}")

for filename in files_to_upload:
    local_path = os.path.join(LOCAL_DIR, filename)
    print(f"\nUploading {filename}...")
    with open(local_path, "rb") as f:
        ftp.storbinary(f"STOR {filename}", f)
    print(f"OK: {filename} uploaded")

ftp.quit()
print("\nDone! All files uploaded.")
