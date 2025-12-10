import os
import uuid
import threading
import time
from flask import Flask, request, jsonify
from supabase import create_client

from enf import extract_enf
from audio_fp import extract_audio_fingerprint
from phash import extract_video_phash

# ================================================================
# SUPABASE INIT
# ================================================================
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# ================================================================
# FILE STORAGE PATH
# ================================================================
UPLOAD_DIR = "/data/files"
os.makedirs(UPLOAD_DIR, exist_ok=True)

app = Flask(__name__)

# ================================================================
# API — /upload
# ================================================================
@app.route("/upload", methods=["POST"])
def upload_slice():
    try:
        user_id = request.form["user_id"]
        name = request.form.get("name", "Untitled")
        sha256 = request.form.get("sha256", "")
        file = request.files["file"]

        # Unique ID for the proof
        proof_id = str(uuid.uuid4())
        filepath = f"{UPLOAD_DIR}/{proof_id}.mp4"
        file.save(filepath)

        # Insert proof
        supabase.table("proofs").insert({
            "id": proof_id,
            "user_id": user_id,
            "hash": sha256,
            "signature": sha256,
            "name": name
        }).execute()

        # Add to forensic queue
        supabase.table("forensic_queue").insert({
            "proof_id": proof_id,
            "user_id": user_id,
            "video_path": filepath,
            "status": "pending"
        }).execute()

        return jsonify({"status": "ok", "proof_id": proof_id})

    except Exception as e:
        print("UPLOAD ERROR:", e)
        return jsonify({"error": str(e)}), 500


@app.route("/")
def health():
    return "API OK", 200

# ================================================================
# WORKER THREAD
# ================================================================
def worker_loop():
    print("Worker thread started...")

    while True:
        try:
            # Fetch next pending task
            task_res = (
                supabase.table("forensic_queue")
                .select("*")
                .eq("status", "pending")
                .limit(1)
                .execute()
            )

            if not task_res.data:
                time.sleep(2)
                continue

            task = task_res.data[0]
            proof_id = task["proof_id"]
            user_id = task["user_id"]
            video_path = task["video_path"]
            task_id = task["id"]

            # Validate file
            if not os.path.exists(video_path):
                supabase.table("forensic_queue").update(
                    {"status": "error_missing_file"}
                ).eq("id", task_id).execute()
                continue

            # Mark as processing
            supabase.table("forensic_queue").update(
                {"status": "processing"}
            ).eq("id", task_id).execute()

            print("Processing:", video_path)

            # Extract forensic data
            enf_hash, enf_png = extract_enf(video_path)
            audio_fp = extract_audio_fingerprint(video_path)
            video_phash = extract_video_phash(video_path)

            # Upload ENF spectrogram PNG
            enf_path = f"{user_id}/{proof_id}_enf.png"
            supabase.storage.from_("main_videos").upload(
                enf_path,
                enf_png,
                file_options={"content-type": "image/png"}
            )

            # Insert forensic results
            supabase.table("forensic_results").insert({
                "proof_id": proof_id,
                "enf_hash": enf_hash,
                "audio_fingerprint": audio_fp,
                "video_phash": video_phash
            }).execute()

            # Delete processed video
            try:
                os.remove(video_path)
            except:
                pass

            # Mark task as done
            supabase.table("forensic_queue").update(
                {"status": "done"}
            ).eq("id", task_id).execute()

            print("✔ DONE:", proof_id)

        except Exception as e:
            print("WORKER ERROR:", e)

        time.sleep(1)

# ================================================================
# START SERVER + WORKER
# ================================================================
if __name__ == "__main__":
    threading.Thread(target=worker_loop, daemon=True).start()
    app.run(host="0.0.0.0", port=10000)
