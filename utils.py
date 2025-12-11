import os
from supabase import create_client

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def upload_file(path: str, data: bytes, mime: str):
    return supabase.storage.from_("main_videos").upload(
        path=path,
        file=data,
        file_options={
            "content-type": mime,
            "upsert": True
        }
    )
