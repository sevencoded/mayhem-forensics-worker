import os
import uuid
import threading
import time
from flask import Flask, request, jsonify
from supabase import create_client

from enf import extract_enf
from audio_fp import extract_audio_fingerprint
from phash import extract_video_phash

# -------------------------
# SUPABASE INIT
# -------------------------
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# -------------------------
# SHARED DISK
# -------------------------
UPLOAD_DIR = "/data/files"
os.makedirs(UPLOAD_DIR, exist_ok=True)

app = Flask(__name__)

# ===============================================================
# API — /upload
# ===============================================================
@app.route("/upload", methods=["POST"])
def upload_slice():
    try:
        user_id = request.form["user_id"]
        name = request.form.get("name", "Untitled")
        sha256 = request.form.get("sha256", "")
        file = request.files["file"]

        proof_id = str(uuid.uuid4())
        filepath = f"{UPLOAD_DIR}/{proof_id}.mp4"
        file.save(filepath)

        supabase.table("proofs").insert({
            "id": proof_id,
            "user_id": user_id,
            "hash": sha256,
            "signature": sha256,
            "name": name
        }).execute()

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

# ===============================================================
# WORKER — radi u POSEBNOM THREAD-u 
# ===============================================================
def worker_loop():
    print("Worker thread started...")

    while True:
        try:
            task = (
                supabase.table("forensic_queue")
                .select("*")
                .eq("status", "pending")
                .limit(1)
                .execute()
            )

            if not task.data:
                time.sleep(2)
                continue

            task = task.data[0]
            proof_id = task["proof_id"]
            user_id = task["user_id"]
            video_path = task["video_path"]

            if not os.path.exists(video_path):
                supabase.table("forensic_queue").update(
                    {"status": "error_missing_file"}
                ).eq("id", task["id"]).execute()
                continue

            supabase.table("forensic_queue").update(
                {"status": "processing"}
            ).eq("id", task["id"]).execute()

            print("Processing:", video_path)

            enf_hash, enf_png = extract_enf(video_path)
            audio_fp = extract_audio_fingerprint(video_path)
            video_phash = extract_video_phash(video_path)

            enf_path = f"{user_id}/{proof_id}_enf.png"
            supabase.storage.from_("main_videos").upload(
                enf_path, enf_png, {"content-type": "image/png"}
            )

            supabase.table("forensic_results").insert({
                "proof_id": proof_id,
                "enf_hash": enf_hash,
                "audio_fingerprint": audio_fp,
                "video_phash": video_phash
            }).execute()

            os.remove(video_path)

            supabase.table("forensic_queue").update(
                {"status": "done"}
            ).eq("id", task["id"]).execute()

            print("✔ DONE:", proof_id)

        except Exception as e:
            print("WORKER ERROR:", e)

        time.sleep(2)

# ===============================================================
# START BOTH
# ===============================================================
if __name__ == "__main__":
    threading.Thread(target=worker_loop, daemon=True).start()
    app.run(host="0.0.0.0", port=10000)
