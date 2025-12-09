import os
import time
import base64
import traceback
from supabase import create_client
from enf import generate_enf_hash_and_image
from audio_fp import generate_audio_fingerprint
from phash import generate_video_phash

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

POLL = 5  # seconds


def process_job(job):
    proof_id = job["proof_id"]
    user_id = job["user_id"]
    b64_data = job["video_path"]

    print(f"[Worker] Processing {proof_id}")

    # decode slice back to bytes
    video_bytes = base64.b64decode(b64_data)

    # save to temp
    tmp_path = f"/tmp/{proof_id}.mp4"
    with open(tmp_path, "wb") as f:
        f.write(video_bytes)

    # run forensic engines
    enf_hash, enf_img = generate_enf_hash_and_image(tmp_path)
    audio_fp = generate_audio_fingerprint(tmp_path)
    video_phash = generate_video_phash(tmp_path)

    # save ENF image to temp
    enf_path = f"/tmp/{proof_id}_enf.png"
    with open(enf_path, "wb") as f:
        f.write(enf_img)

    # store forensic results
    supabase.table("forensic_results").insert({
        "proof_id": proof_id,
        "enf_hash": enf_hash,
        "audio_fingerprint": audio_fp,
        "video_phash": video_phash,
    }).execute()

    # update queue
    supabase.table("forensic_queue") \
        .update({"status": "done"}) \
        .eq("id", job["id"]).execute()

    try:
        os.remove(tmp_path)
        os.remove(enf_path)
    except:
        pass

    print(f"[Worker] COMPLETED {proof_id}")


while True:
    try:
        job = supabase.table("forensic_queue") \
                      .select("*") \
                      .eq("status", "pending") \
                      .limit(1).execute().data

        if job:
            process_job(job[0])
        else:
            print("[Worker] No pending jobs")

    except Exception as e:
        print("Worker error:", e)
        traceback.print_exc()

    time.sleep(POLL)
