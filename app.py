# app.py
import os
import traceback
import threading
import time
import uuid

from flask import Flask, request, jsonify

from utils import supabase, upload_file
from enf import extract_enf
from audio_fp import extract_audio_fingerprint
from phash import extract_video_phash

# Shared persistent Render disk
UPLOAD_DIR = "/data/files"
os.makedirs(UPLOAD_DIR, exist_ok=True)

app = Flask(__name__)


# =========================================================
# WORKER — PROCESSES 1 JOB AT A TIME (SAFE FOR 1000/day)
# =========================================================
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
                time.sleep(1)
                continue

            job = job_res.data[0]
            queue_id = job["id"]
            proof_id = job["proof_id"]
            user_id = job["user_id"]
            video_path = job["video_path"]

            print(f"[WORKER] Processing job {queue_id} → proof {proof_id}")

            # Update status
            supabase.table("forensic_queue").update(
                {"status": "processing"}
            ).eq("id", queue_id).execute()

            try:
                # -------------------------------------------
                # FULL FORENSIC PIPELINE (ENF, audio FP, pHash)
                # -------------------------------------------
                enf_hash, enf_png = extract_enf(video_path)
                audio_fp = extract_audio_fingerprint(video_path)
                video_phash = extract_video_phash(video_path)

                # Save ENF image (PNG) u isti bucket kao i video
                enf_path = f"{user_id}/{proof_id}_enf.png"
                upload_file(enf_path, enf_png, "image/png")

                # Save forensic results u bazu
                supabase.table("forensic_results").insert(
                    {
                        "proof_id": proof_id,
                        "enf_hash": enf_hash,
                        "audio_fingerprint": audio_fp,
                        "video_phash": video_phash,
                    }
                ).execute()

                # Delete slice sa diska
                try:
                    os.remove(video_path)
                except Exception:
                    pass

                supabase.table("forensic_queue").update(
                    {"status": "completed"}
                ).eq("id", queue_id).execute()

                print(f"[WORKER] ✓ DONE → {proof_id}")

            except Exception as e:
                print("FORENSIC ERROR:", e)
                traceback.print_exc()

                supabase.table("forensic_queue").update(
                    {"status": "failed"}
                ).eq("id", queue_id).execute()

        except Exception as e:
            print("WORKER LOOP ERROR:", e)
            traceback.print_exc()

        time.sleep(1)


# Start worker thread (ako se ovo vrti kao web servis)
threading.Thread(target=process_pending_jobs, daemon=True).start()


# =========================================================
# UPLOAD ENDPOINT — INSTANT RESPONSE (FAST)
# =========================================================
@app.route("/upload", methods=["POST"])
def upload():
    try:
        user_id = request.form["user_id"]
        name = request.form["name"]
        sha256 = request.form["sha256"]
        file = request.files["file"]

        proof_id = str(uuid.uuid4())
        filepath = f"{UPLOAD_DIR}/{proof_id}.mp4"
        file.save(filepath)

        # upis u proofs
        supabase.table("proofs").insert(
            {
                "id": proof_id,
                "user_id": user_id,
                "name": name,
                "hash": sha256,
                "signature": sha256,
            }
        ).execute()

        # stavljanje u forenzički queue
        supabase.table("forensic_queue").insert(
            {
                "proof_id": proof_id,
                "user_id": user_id,
                "video_path": filepath,
                "status": "pending",
            }
        ).execute()

        return jsonify({"ok": True, "proof_id": proof_id})

    except Exception as e:
        print("UPLOAD ERROR:", e)
        return jsonify({"error": str(e)}), 500


@app.route("/")
def health():
    return "WORKER + API OK", 200


if __name__ == "__main__":
    # Lokalno testiranje – na Renderu koristiš startCommand iz render.yaml
    app.run(host="0.0.0.0", port=10000)
