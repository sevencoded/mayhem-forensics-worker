# utils.py
import os
from supabase import create_client, Client

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError("SUPABASE_URL or SUPABASE_SERVICE_KEY not set in environment")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


def upload_file(path: str, data: bytes, mime: str):
    """
    Helper za upload u Supabase Storage (bucket: main_videos).

    path  – relativna putanja u bucketu (npr. 'user_id/proof_enf.png')
    data  – raw bytes
    mime  – npr. 'image/png'
    """
    # Supabase-py API: upload(file=..., path=..., file_options={...})
    return supabase.storage.from_("main_videos").upload(
        file=data,
        path=path,
        file_options={
            "content-type": mime,
            "cache-control": "3600",
            "upsert": "true",
        },
    )
