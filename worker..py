# worker.py
import os
import time
import traceback

from utils import supabase, upload_file
from enf import extract_enf
from audio_fp import extract_audio_fingerprint
from phash import extract_video_phash

def worker_loop():
    print("WORKER STARTED")

    while True:
        try:
            job_res = supabase.table("forensic_queue")\
                .select("*")\
                .eq("status", "pending")\
                .limit(1)\
                .execute()

            if not job_res.data:
                time.sleep(1)
                continue

            job = job_res.data[0]

            qid = job["id"]
            proof_id = job["proof_id"]
            user_id = job["user_id"]
            file_path = job["file_path"]

            # Mark job as processing
            supabase.table("forensic_queue").update({
                "status": "processing"
            }).eq("id", qid).execute()

            try:
                # Run forensic processing
                enf_hash, enf_png = extract_enf(file_path)
                audio_fp = extract_audio_fingerprint(file_path)
                video_phash = extract_video_phash(file_path)

                # Upload ENF result image
                upload_file(f"{user_id}/{proof_id}_enf.png", enf_png, "image/png")

                # Save results
                supabase.table("forensic_results").insert({
                    "proof_id": proof_id,
                    "enf_hash": enf_hash,
                    "audio_fingerprint": audio_fp,
                    "video_phash": video_phash
                }).execute()

                # Cleanup: delete slice file
                if os.path.exists(file_path):
                    os.remove(file_path)

                supabase.table("forensic_queue").update({
                    "status": "completed"
                }).eq("id", qid).execute()

            except Exception as e:
                print("PROCESS ERROR:", e)
                traceback.print_exc()

                supabase.table("forensic_queue").update({
                    "status": "failed"
                }).eq("id", qid).execute()

        except Exception as e:
            print("WORKER LOOP ERROR:", e)
            traceback.print_exc()

        time.sleep(1)
