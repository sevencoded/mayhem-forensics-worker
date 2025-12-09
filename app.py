import os
import traceback
import threading
import time
import uuid
import tempfile
from flask import Flask, request, jsonify
from supabase import create_client

from enf import generate_enf_hash_and_image
from audio_fp import generate_audio_fingerprint
from phash import generate_video_phash
from utils import upload_file

# ---------------------------------------------------------
# SUPABASE INIT
# ---------------------------------------------------------
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

app = Flask(__name__)

# ---------------------------------------------------------
# BACKGROUND WORKER LOOP
# ---------------------------------------------------------

def process_pending_jobs():
    while True:
        try:
            jobs = supabase.table("forensic_queue").select("*").eq("status", "pending").limit(1).execute()

            if len(jobs.data) == 0:
                time.sleep(2)
                continue

            job = jobs.data[0]
            queue_id = job["id"]
            proof_id = job["proof_id"]
            user_id = job["user_id"]
            video_path = job["video_path"]

            print(f"Processing forensic job: {queue_id}")

            try:
                # ---------------------------------------------------------
                # FORENSIC PROCESSING
                # ---------------------------------------------------------
                enf_hash, enf_img = generate_enf_hash_and_image(video_path)
                audio_fp = generate_audio_fingerprint(video_path)
                video_phash = generate_video_phash(video_path)

                # upload ENF PNG
                enf_name = f"{user_id}_{proof_id}_enf.png"
                upload_file(f"enf/{enf_name}", enf_img, "image/png")

                # write forensic results
                supabase.table("forensic_results").insert({
                    "proof_id": proof_id,
                    "enf_hash": enf_hash,
                    "audio_fingerprint": audio_fp,
                    "video_phash": video_phash
                }).execute()

                # mark as completed
                supabase.table("forensic_queue").update({
                    "status": "completed"
                }).eq("id", queue_id).execute()

                print(f"Forensic completed for proof {proof_id}")

            except Exception as e:
                print("ERROR in forensic worker:", e)
                traceback.print_exc()

                supabase.table("forensic_queue").update({
                    "status": "failed"
                }).eq("id", queue_id).execute()

        except Exception as e:
            print("Worker loop crash:", e)
            traceback.print_exc()

        time.sleep(2)


# start worker thread
threading.Thread(target=process_pending_jobs, daemon=True).start()


# ---------------------------------------------------------
# UPLOAD ENDPOINT – returns instantly
# ---------------------------------------------------------
@app.route("/upload", methods=["POST"])
def upload():
    try:
        user_id = request.form.get("user_id")
        name = request.form.get("name")
        sha256 = request.form.get("sha256")

        if not user_id or not name or not sha256:
            return jsonify({"error": "Missing fields"}), 400

        file = request.files.get("file")
        if not file:
            return jsonify({"error": "Missing video file"}), 400

        # save temp file
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
        tmp.write(file.read())
        tmp.close()
        local_path = tmp.name

        # create proof entry
        proof_id = str(uuid.uuid4())

        supabase.table("proofs").insert({
            "id": proof_id,
            "user_id": user_id,
            "name": name,
            "hash": sha256,
            "signature": str(uuid.uuid4())
        }).execute()

        # add queue job
        supabase.table("forensic_queue").insert({
            "proof_id": proof_id,
            "user_id": user_id,
            "video_path": local_path,
            "status": "pending"
        }).execute()

        return jsonify({
            "ok": True,
            "proof_id": proof_id,
            "status": "pending"
        }), 200

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port)
