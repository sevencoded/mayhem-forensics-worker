import time
import os
from supabase import create_client
from enf import extract_enf
from audio_fp import extract_audio_fingerprint
from phash import extract_video_phash

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


def upload_enf_png(user_id, proof_id, png_bytes):
    path = f"{user_id}/{proof_id}_enf.png"
    supabase.storage.from_("main_videos").upload(
        path=path,
        file=png_bytes,
        file_options={"content-type": "image/png"}
    )
    return path


while True:
    try:
        queue = (
            supabase.table("forensic_queue")
            .select("*")
            .eq("status", "pending")
            .limit(1)
            .execute()
        )

        if not queue.data:
            time.sleep(3)
            continue

        task = queue.data[0]
        proof_id = task["proof_id"]
        user_id = task["user_id"]
        video_path = task["video_path"]

        supabase.table("forensic_queue").update({"status": "processing"}).eq("id", task["id"]).execute()

        enf_hash, enf_png = extract_enf(video_path)
        audio_fp = extract_audio_fingerprint(video_path)
        video_phash = extract_video_phash(video_path)

        enf_path = upload_enf_png(user_id, proof_id, enf_png)

        supabase.table("forensic_results").insert({
            "proof_id": proof_id,
            "enf_hash": enf_hash,
            "audio_fingerprint": audio_fp,
            "video_phash": video_phash
        }).execute()

        # Delete local slice
        if os.path.exists(video_path):
            os.remove(video_path)

        supabase.table("forensic_queue").update({"status": "done"}).eq("id", task["id"]).execute()

    except Exception as e:
        print("Worker error:", e)

    time.sleep(3)
