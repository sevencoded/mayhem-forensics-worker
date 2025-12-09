import os
import time
import traceback
from supabase import create_client
from enf import generate_enf_hash_and_image
from audio_fp import generate_audio_fingerprint
from phash import generate_video_phash

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

POLL_INTERVAL = 10  # every 10 seconds

def process_job(job):
    proof_id = job["proof_id"]
    user_id = job["user_id"]
    path = job["video_path"]

    print(f"Processing forensic job for proof {proof_id}")

    # Forensic outputs
    enf_hash, enf_image_bytes = generate_enf_hash_and_image(path)
    audio_fp = generate_audio_fingerprint(path)
    video_phash = generate_video_phash(path)

    # Save ENF image
    supabase.storage.from_("main_videos").upload(
        f"enf/{user_id}_{proof_id}_enf.png",
        enf_image_bytes,
        {"content-type": "image/png"}
    )

    # Save forensic results
    supabase.table("forensic_results").insert({
        "proof_id": proof_id,
        "enf_hash": enf_hash,
        "audio_fingerprint": audio_fp,
        "video_phash": video_phash,
    }).execute()

    # Mark job as done
    supabase.table("forensic_queue").update({"status": "done"}) \
        .eq("id", job["id"]).execute()

    # Remove temp slice
    try:
        os.remove(path)
    except:
        pass


while True:
    try:
        jobs = supabase.table("forensic_queue") \
                       .select("*") \
                       .eq("status", "pending") \
                       .limit(1) \
                       .execute().data

        if jobs:
            process_job(jobs[0])
        else:
            print("No pending jobs.")

    except Exception as e:
        print("Worker error:", e)
        traceback.print_exc()

    time.sleep(POLL_INTERVAL)
