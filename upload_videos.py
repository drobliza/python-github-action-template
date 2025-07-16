import os
import google.auth
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.auth.transport.requests import Request
import json
import time
from datetime import datetime, timedelta

# وظيفة لتحميل بيانات الاعتماد من GitHub Secrets
def load_credentials(secret_name):
    # تحميل البيانات من GitHub secrets
    credentials_json = os.getenv(secret_name)
    return json.loads(credentials_json)

# وظيفة لتوثيق الوصول إلى Google Drive
def authenticate_google_drive():
    credentials_info = load_credentials('GOOGLE_DRIVE_CREDENTIALS')
    credentials, project = google.auth.load_credentials_from_info(credentials_info)
    drive_service = build('drive', 'v3', credentials=credentials)
    return drive_service

# وظيفة لتوثيق الوصول إلى YouTube API
def authenticate_youtube():
    credentials_info = load_credentials('YOUTUBE_API_CREDENTIALS')
    credentials, project = google.auth.load_credentials_from_info(credentials_info)
    youtube_service = build('youtube', 'v3', credentials=credentials)
    return youtube_service

# الحصول على الملفات من Google Drive
def list_drive_files(drive_service, folder_id):
    results = drive_service.files().list(q=f"'{folder_id}' in parents", spaces='drive').execute()
    files = results.get('files', [])
    return files

# رفع الفيديو إلى YouTube
def upload_video_to_youtube(youtube_service, file_path, title, description):
    request_body = {
        'snippet': {
            'title': title,
            'description': description,
            'tags': ['auto-uploaded'],
        },
        'status': {
            'privacyStatus': 'public',  # يمكن تغييره إلى 'private' أو 'unlisted'
        },
    }

    media = MediaFileUpload(file_path, mimetype='video/*', resumable=True)

    upload_request = youtube_service.videos().insert(
        part="snippet,status",
        body=request_body,
        media_body=media
    )

    upload_request.execute()

# تحميل الفيديو من Google Drive
def download_video(drive_service, file_id):
    request = drive_service.files().get_media(fileId=file_id)
    file_name = f"video_{file_id}.mp4"
    with open(file_name, 'wb') as f:
        downloader = MediaIoBaseDownload(f, request)
        done = False
        while done is False:
            status, done = downloader.next_chunk()
    return file_name

# جدولة رفع الفيديوهات
def schedule_videos(drive_service, youtube_service):
    folder_id = '1_iPtcfFs3TpusMr9THwTc31SWtLtwccZ'  # ID المجلد الخاص بك في Google Drive
    
    # الحصول على الملفات من Google Drive
    files = list_drive_files(drive_service, folder_id)

    # وقت التحميل لكل فيديو
    times_to_upload = [
        {"time": datetime.strptime("12:00", "%H:%M"), "index": 0},  # الفيديو الأول في الساعة 12:00
        {"time": datetime.strptime("16:00", "%H:%M"), "index": 1},  # الفيديو الثاني في الساعة 16:00
        {"time": datetime.strptime("20:00", "%H:%M"), "index": 2},  # الفيديو الثالث في الساعة 20:00
    ]
    
    now = datetime.now()

    for upload_time in times_to_upload:
        video_file = files[upload_time["index"]]
        video_path = download_video(drive_service, video_file['id'])
        
        # حساب الفرق بين الوقت الحالي ووقت التحميل المحدد
        wait_time = (upload_time["time"] - now).total_seconds()

        if wait_time > 0:
            print(f"Waiting {wait_time / 60} minutes for the next upload at {upload_time['time']}")
            time.sleep(wait_time)  # الانتظار حتى الوقت المحدد
        
        # رفع الفيديو إلى YouTube
        print(f"Uploading video {video_file['name']} to YouTube...")
        upload_video_to_youtube(youtube_service, video_path, video_file['name'], 'Video uploaded via GitHub Action')

# الوظيفة الرئيسية
def main():
    drive_service = authenticate_google_drive()
    youtube_service = authenticate_youtube()
    schedule_videos(drive_service, youtube_service)

if __name__ == "__main__":
    main()
