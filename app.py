import time
import os
import traceback
from supabase import create_client
from utils import download_file, upload_file, delete_file
from enf import generate_enf_hash_and_image
from audio_fp import generate_audio_fingerprint
from phash import generate_video_phash

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def process_job(job):
    proof_id = job["proof_id"]
    user_id = job["user_id"]
    video_path = job["video_path"]

    print(f"=== PROCESSING {proof_id} ===")

    local_video = download_file(video_path)

    # --- FORENSIC PROCESSING ---
    enf_hash, enf_image_bytes = generate_enf_hash_and_image(local_video)
    audio_fp = generate_audio_fingerprint(local_video)
    video_phash = generate_video_phash(local_video)

    # upload ENF image
    enf_name = f"{user_id}_{proof_id}_enf.png"
    upload_file(f"enf/{enf_name}", enf_image_bytes, "image/png")

    # delete original video
    delete_file(video_path)

    # insert forensic results
    supabase.table("forensic_results").insert({
        "proof_id": proof_id,
        "enf_hash": enf_hash,
        "audio_fingerprint": audio_fp,
        "video_phash": video_phash,
        "metadata_hash": None,
        "chain_hash": None
    }).execute()

    # mark queue done
    supabase.table("forensic_queue").update({"status": "done"}).eq("id", job["id"]).execute()

    print("=== DONE ===")

def main_loop():
    print("Worker started! Running 24/7...")

    while True:
        try:
            jobs = (
                supabase.table("forensic_queue")
                .select("*")
                .eq("status", "pending")
                .limit(1)
                .execute()
            )

            if jobs.data:
                process_job(jobs.data[0])
            else:
                time.sleep(1)

        except Exception as e:
            print("ERROR:", e)
            traceback.print_exc()
            time.sleep(2)

if __name__ == "__main__":
    main_loop()
