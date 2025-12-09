import os
import time
import uuid
import traceback

from supabase import create_client
from enf import generate_enf_hash_and_image
from audio_fp import generate_audio_fingerprint
from phash import generate_video_phash

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

POLL_INTERVAL = 10  # seconds


def upload_to_storage(path: str, data: bytes, mime="image/png"):
    """Upload ENF PNG to Supabase storage."""
    resp = supabase.storage.from_("main_videos").upload(
        path, data, {"content-type": mime, "upsert": True}
    )
    return resp


def process_job(job):
    try:
        proof_id = job["proof_id"]
        user_id = job["user_id"]
        slice_path = job["video_path"]

        print(f"[WORKER] Processing proof {proof_id} ...")

        # ===============================
        # 1. FORENSIC PROCESSING
        # ===============================
        enf_hash, enf_png = generate_enf_hash_and_image(slice_path)
        audio_fp = generate_audio_fingerprint(slice_path)
        video_phash = generate_video_phash(slice_path)

        # ===============================
        # 2. SAVE ENF PNG TO STORAGE
        # ===============================
        filename = f"enf/{user_id}_{proof_id}.png"
        upload_to_storage(filename, enf_png)

        # ===============================
        # 3. SAVE RESULTS INTO DB
        # ===============================
        supabase.table("forensic_results").insert({
            "proof_id": proof_id,
            "enf_hash": enf_hash,
            "audio_fingerprint": audio_fp,
            "video_phash": video_phash,
            "metadata_hash": None,
            "chain_hash": None,
        }).execute()

        # ===============================
        # 4. REMOVE FILE FROM QUEUE
        # ===============================
        supabase.table("forensic_queue").delete().eq("id", job["id"]).execute()

        # ===============================
        # 5. DELETE SLICE FROM DISK
        # ===============================
        if os.path.exists(slice_path):
            os.remove(slice_path)

        print(f"[WORKER] Completed {proof_id}")

    except Exception as e:
        print("[WORKER ERROR]", e)
        traceback.print_exc()


def worker_loop():
    print("=== WORKER STARTED ===")

    while True:
        try:
            res = supabase.table("forensic_queue") \
                .select("*") \
                .limit(1) \
                .execute()

            if not res.data:
                time.sleep(POLL_INTERVAL)
                continue

            job = res.data[0]
            process_job(job)

        except Exception as e:
            print("[LOOP ERROR]", e)
            traceback.print_exc()

        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    worker_loop()
