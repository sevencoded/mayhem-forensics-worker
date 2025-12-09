import os
import time
import uuid
import traceback
from supabase import create_client
from enf import extract_enf_and_spectrogram
from audio_fp import extract_audio_fingerprint
from phash import extract_video_phash

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

QUEUE_DIR = "queue_slices"
os.makedirs(QUEUE_DIR, exist_ok=True)


# --------------------------------------------------------
# Upload ENF spectrogram to Supabase
# --------------------------------------------------------
def upload_enf_image(user_id, proof_id, png_bytes):
    path = f"{user_id}/{proof_id}_enf.png"

    supabase.storage \
        .from_("main_videos") \
        .upload(
            path,
            png_bytes,
            {"content-type": "image/png"},
            upsert=True
        )


# --------------------------------------------------------
# PROCESS JOB
# --------------------------------------------------------
def process_job(job):
    proof_id = job["proof_id"]
    user_id = job["user_id"]
    video_path = job["video_path"]

    print(f"\n[WORKER] Processing {proof_id}")

    if not os.path.exists(video_path):
        print("[WORKER] Slice missing — marking failed.")
        supabase.table("forensic_queue").update({"status": "failed"}).eq("id", job["id"]).execute()
        return

    try:
        # -----------------------------------------
        # 1. ENF + PNG
        # -----------------------------------------
        enf_hash, png_bytes = extract_enf_and_spectrogram(video_path)

        if png_bytes:
            upload_enf_image(user_id, proof_id, png_bytes)

        # -----------------------------------------
        # 2. Audio Fingerprint
        # -----------------------------------------
        audio_fp = extract_audio_fingerprint(video_path)

        # -----------------------------------------
        # 3. Video pHash
        # -----------------------------------------
        video_phash = extract_video_phash(video_path)

        # -----------------------------------------
        # 4. Save results
        # -----------------------------------------
        supabase.table("forensic_results").insert({
            "proof_id": proof_id,
            "enf_hash": enf_hash,
            "audio_fingerprint": audio_fp,
            "video_phash": video_phash
        }).execute()

        # Mark done
        supabase.table("forensic_queue").update({"status": "done"}).eq("id", job["id"]).execute()

        print("[WORKER] Completed:", proof_id)

    except Exception as e:
        print("[WORKER] ERROR:", e)
        print(traceback.format_exc())

        supabase.table("forensic_queue").update({"status": "error"}).eq("id", job["id"]).execute()

    finally:
        # Cleanup slice to save space
        if os.path.exists(video_path):
            os.remove(video_path)
            print("[WORKER] Removed slice:", video_path)


# --------------------------------------------------------
# MAIN WORKER LOOP
# --------------------------------------------------------
def run_worker():
    print("\n[WORKER] Started forensic engine loop (every 10s)\n")

    while True:
        try:
            jobs = supabase.table("forensic_queue") \
                .select("*") \
                .eq("status", "pending") \
                .limit(3) \
                .execute()

            pending = jobs.data or []

            if not pending:
                print("[WORKER] No jobs — sleeping...")
                time.sleep(10)
                continue

            print(f"[WORKER] Found {len(pending)} pending jobs")

            for job in pending:
                process_job(job)

        except Exception as e:
            print("\n[WORKER] LOOP ERROR:", e)
            print(traceback.format_exc())

        time.sleep(10)


if __name__ == "__main__":
    run_worker()
