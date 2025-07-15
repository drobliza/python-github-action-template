import os
import time
import pickle
import json
import datetime
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from pydrive2.auth import GoogleAuth
from pydrive2.drive import GoogleDrive

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
DRIVE_FOLDER_NAME = "ShortsToUpload"
UPLOADED_LOG = "uploaded_videos.json"
MAX_VIDEOS_PER_DAY = 3

def authenticate_youtube():
    creds = None
    if os.path.exists("token_upload.pickle"):
        with open("token_upload.pickle", "rb") as token:
            creds = pickle.load(token)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file("client_secret.json", SCOPES)
            creds = flow.run_local_server(port=0)
        with open("token_upload.pickle", "wb") as token:
            pickle.dump(creds, token)
    return build("youtube", "v3", credentials=creds)

def authenticate_drive():
    gauth = GoogleAuth()
    gauth.LoadCredentialsFile("drive_creds.txt")
    if gauth.credentials is None:
        gauth.LocalWebserverAuth()
    elif gauth.access_token_expired:
        gauth.Refresh()
    else:
        gauth.Authorize()
    gauth.SaveCredentialsFile("drive_creds.txt")
    return GoogleDrive(gauth)

def load_uploaded():
    if os.path.exists(UPLOADED_LOG):
        with open(UPLOADED_LOG, "r", encoding="utf-8") as f:
            return set(json.load(f))
    return set()

def save_uploaded(video_name):
    uploaded = load_uploaded()
    uploaded.add(video_name)
    with open(UPLOADED_LOG, "w", encoding="utf-8") as f:
        json.dump(list(uploaded), f, ensure_ascii=False, indent=2)

def get_videos_from_drive(drive):
    folder_list = drive.ListFile({"q": "title='{}' and mimeType='application/vnd.google-apps.folder' and trashed=false".format(DRIVE_FOLDER_NAME)}).GetList()
    if not folder_list:
        print(f"❌ المجلد '{DRIVE_FOLDER_NAME}' غير موجود في Google Drive")
        return []
    folder_id = folder_list[0]['id']
    uploaded = load_uploaded()
    file_list = drive.ListFile({"q": f"'{folder_id}' in parents and mimeType='video/mp4' and trashed=false"}).GetList()
    videos = [f for f in file_list if f['title'] not in uploaded]
    return videos[:MAX_VIDEOS_PER_DAY]

def download_video(file, local_path):
    file.GetContentFile(local_path)
    print(f"⬇️ تم تحميل: {file['title']}")

def upload_video_to_youtube(youtube, file_path, title):
    print(f"⬆️ رفع الفيديو: {title}")
    request_body = {
        "snippet": {
            "title": title,
            "description": "",
            "categoryId": "22"
        },
        "status": {
            "privacyStatus": "private",
            "selfDeclaredMadeForKids": False
        }
    }
    media_file = MediaFileUpload(file_path, chunksize=-1, resumable=True, mimetype="video/*")
    upload_request = youtube.videos().insert(
        part="snippet,status",
        body=request_body,
        media_body=media_file
    )
    response = None
    while response is None:
        status, response = upload_request.next_chunk()
        if status:
            print(f"📊 التقدم: {int(status.progress() * 100)}%")
    print(f"✅ تم رفع الفيديو: {title}")

def main():
    youtube = authenticate_youtube()
    drive = authenticate_drive()
    videos = get_videos_from_drive(drive)
    if not videos:
        print("📂 لا توجد فيديوهات جديدة في مجلد Google Drive")
        return
    for file in videos:
        filename = file['title']
        local_path = filename
        download_video(file, local_path)
        upload_video_to_youtube(youtube, local_path, os.path.splitext(filename)[0])
        save_uploaded(filename)
        os.remove(local_path)
        time.sleep(1)

if __name__ == "__main__":
    main()
