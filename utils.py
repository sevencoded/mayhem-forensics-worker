import os
import tempfile
from supabase import create_client

supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_KEY"))

def download_file(path):
    res = supabase.storage.from_("main_videos").download(path)
    temp = tempfile.NamedTemporaryFile(delete=False, suffix=".video")
    temp.write(res)
    temp.close()
    return temp.name

def upload_file(path, bytes_data, content_type):
    supabase.storage.from_("main_videos").upload(path, bytes_data, {
        "contentType": content_type,
        "upsert": True
    })

def delete_file(path):
    supabase.storage.from_("main_videos").remove([path])
