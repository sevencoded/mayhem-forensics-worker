import os
from supabase import create_client

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError("SUPABASE_URL or SUPABASE_SERVICE_KEY not set")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


def upload_file(path: str, data: bytes, mime: str):
    return supabase.storage.from_("main_videos").upload(
        file=data,
        path=path,
        file_options={
            "content-type": mime,
            "cache-control": "3600",
            "upsert": "true",
        },
    )
