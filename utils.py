import os
from supabase import create_client, Client

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def upload_file(path: str, data: bytes, mime: str):
    supabase.storage.from_("main_videos").upload(
        file=data,
        path=path,
        file_options={"content-type": mime}
    )
