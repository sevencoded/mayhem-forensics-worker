import os
import time
import base64
from supabase import create_client
import traceback

from enf import generate_enf_hash_and_image
from audio_fp import generate_audio_fingerprint
from phash import generate_video_phash

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

POLL_INTERVAL = 5  # seconds


def process(job):
    proof_id = job["proof_id"]
    q_id = job["id"]
    b64_data = job["video_path"]

    print(f"[Worker] Processing: {proof_id}")

    # decode slice
    video_bytes = base64.b64decode(b64_data)

    # save temporary file
    temp_path = f"/tmp/{proof_id}.mp4"
    with open(temp_path, "wb") as f:
        f.write(video_bytes)

    try:
        # Run forensic analysis
        enf_hash, enf_img = generate_enf_hash_and_image(temp_path)
        audio_fp = generate_audio_fingerprint(temp_path)
        video_phash = generate_video_phash(temp_path)

        # save ENF image temporarily
        enf_path = f"/tmp/{proof_id}_enf.png"
        with open(enf_path, "wb") as f:
            f.write(enf_img)

        # Save forensic results
        supabase.table("forensic_results").insert({
            "proof_id": proof_id,
            "enf_hash": enf_hash,
            "audio_fingerprint": audio_fp,
            "video_phash": video_phash,
        }).execute()

        # Mark job as done
        supabase.table("forensic_queue").update({
            "status": "done",
            "video_path": None  # delete slice immediately
        }).eq("id", q_id).execute()

        print(f"[Worker] Completed: {proof_id}")

    except Exception as e:
        print(f"[Worker ERROR] {e}")
        traceback.print_exc()

        supabase.table("forensic_queue").update({
            "status": "error"
        }).eq("id", q_id).execute()

    finally:
        # Cleanup temp files
        try:
            if os.path.exists(temp_path):
                os.remove(temp_path)
            if os.path.exists(enf_path):
                os.remove(enf_path)
        except:
            pass


# MAIN LOOP
while True:
    try:
        job = supabase.table("forensic_queue") \
            .select("*") \
            .eq("status", "pending") \
            .limit(1) \
            .execute().data

        if job:
            process(job[0])
        else:
            print("[Worker] No pending jobs")

    except Exception as e:
        print("Worker loop error:", e)

    time.sleep(POLL_INTERVAL)
