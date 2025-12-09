import os
from supabase import create_client

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def upload_file(path, bytes, mime):
    supabase.storage.from_("main_videos").upload(
        path, bytes, {"content-type": mime}
    )
