import os
import traceback
import threading
import time
import uuid
from flask import Flask, request, jsonify
from supabase import create_client

from enf import extract_enf          # NOVA verzija koju si poslao
from audio_fp import extract_audio_fingerprint
from phash import extract_video_phash

# ---------------------------------------------------------
# SUPABASE INIT
# ---------------------------------------------------------
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

app = Flask(__name__)

# Shared disk
UPLOAD_DIR = "/data/files"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# ---------------------------------------------------------
# BACKGROUND WORKER LOOP
# ---------------------------------------------------------
def process_pending_jobs():
    print("Worker started...")

    while True:
        try:
            job_res = (
                supabase.table("forensic_queue")
                .select("*")
                .eq("status", "pending")
                .limit(1)
                .execute()
            )

            if not job_res.data:
                time.sleep(2)
                continue

            job = job_res.data[0]
            queue_id = job["id"]
            proof_id = job["proof_id"]
            user_id = job["user_id"]
            video_path = job["video_path"]

            print("Processing job:", queue_id)

            # Mark job as processing
            supabase.table("forensic_queue").update(
                {"status": "processing"}
            ).eq("id", queue_id).execute()

            try:
                # -------------------------------------------
                # FORENSIC PIPELINE (slice-based)
                # -------------------------------------------
                enf_hash, enf_png = extract_enf(video_path)
                audio_fp = extract_audio_fingerprint(video_path)
                video_phash = extract_video_phash(video_path)

                # -------------------------------------------
                # Upload ENF PNG to storage
                # -------------------------------------------
                enf_path = f"{user_id}/{proof_id}_enf.png"
                supabase.storage.from_("main_videos").upload(
                    enf_path,
                    enf_png,
                    {"content-type": "image/png"}
                )

                # -------------------------------------------
                # Save forensic results
                # -------------------------------------------
                supabase.table("forensic_results").insert({
                    "proof_id": proof_id,
                    "enf_hash": enf_hash,
                    "audio_fingerprint": audio_fp,
                    "video_phash": video_phash
                }).execute()

                # Remove slice file after processing
                try:
                    os.remove(video_path)
                except:
                    pass

                supabase.table("forensic_queue").update(
                    {"status": "completed"}
                ).eq("id", queue_id).execute()

                print("✔ JOB DONE:", proof_id)

            except Exception as e:
                print("Worker forensic error:", e)
                traceback.print_exc()

                supabase.table("forensic_queue").update(
                    {"status": "failed"}
                ).eq("id", queue_id).execute()

        except Exception as e:
            print("Worker loop crash:", e)
            traceback.print_exc()

        time.sleep(1)


# Start worker thread
threading.Thread(target=process_pending_jobs, daemon=True).start()

# ---------------------------------------------------------
# UPLOAD ENDPOINT — RETURNS INSTANTLY
# ---------------------------------------------------------
@app.route("/upload", methods=["POST"])
def upload():
    try:
        user_id = request.form["user_id"]
        name = request.form["name"]
        sha256 = request.form["sha256"]

        file = request.files["file"]
        proof_id = str(uuid.uuid4())

        # Save slice to shared disk
        filepath = f"{UPLOAD_DIR}/{proof_id}.mp4"
        file.save(filepath)

        # Save proof
        supabase.table("proofs").insert({
            "id": proof_id,
            "user_id": user_id,
            "name": name,
            "hash": sha256,
            "signature": sha256
        }).execute()

        # Queue job
        supabase.table("forensic_queue").insert({
            "proof_id": proof_id,
            "user_id": user_id,
            "video_path": filepath,
            "status": "pending"
        }).execute()

        return jsonify({"ok": True, "proof_id": proof_id})

    except Exception as e:
        print("UPLOAD ERROR:", e)
        return jsonify({"error": str(e)}), 500


@app.route("/")
def health():
    return "WORKER + API OK", 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
