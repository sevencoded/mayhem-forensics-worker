import os
import uuid
import tempfile
import time
from flask import Flask, request, jsonify

from utils import supabase, upload_file
from enf import extract_enf
from audio_fp import extract_audio_fingerprint
from phash import extract_video_phash

app = Flask(__name__)

MAX_SLICE_SIZE = 10 * 1024 * 1024  # 10MB
RETRY_AFTER = 5                   # seconds

# 🔒 SINGLE SLOT
ACTIVE_JOB = False


@app.route("/capacity", methods=["GET"])
def capacity():
    return jsonify({
        "busy": ACTIVE_JOB,
        "retry_after": RETRY_AFTER
    }), 200


@app.route("/upload", methods=["POST"])
def upload():
    global ACTIVE_JOB
    temp_path = None

    # ❌ ako je server zauzet
    if ACTIVE_JOB:
        return jsonify({
            "error": "Server busy",
            "retry_after": RETRY_AFTER
        }), 429

    try:
        ACTIVE_JOB = True

        # ----------------------------
        # 1. VALIDATION
        # ----------------------------
        user_id = request.form.get("user_id")
        name = request.form.get("name")
        sha256 = request.form.get("sha256")
        file = request.files.get("file")

        if not all([user_id, name, sha256, file]):
            return jsonify({"error": "Missing fields"}), 400

        slice_bytes = file.read()
        if len(slice_bytes) > MAX_SLICE_SIZE:
            return jsonify({"error": "Slice too large"}), 413

        proof_id = str(uuid.uuid4())

        # ----------------------------
        # 2. SAVE TEMP SLICE
        # ----------------------------
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
            tmp.write(slice_bytes)
            temp_path = tmp.name

        # ----------------------------
        # 3. FORENSIC PIPELINE
        # ----------------------------
        enf_hash, enf_png = extract_enf(temp_path)
        audio_fp = extract_audio_fingerprint(temp_path)
        try:
          video_phash = extract_video_phash(temp_path)
           except Exception as e:
              print("pHash skipped:", e)
               video_phash = None
        # 4. SAVE RESULTS
        # ----------------------------
        supabase.table("proofs").insert({
            "id": proof_id,
            "user_id": user_id,
            "name": name,
            "hash": sha256,
            "signature": sha256
        }).execute()

        supabase.table("forensic_results").insert({
            "proof_id": proof_id,
            "enf_hash": enf_hash,
            "audio_fingerprint": audio_fp,
            "video_phash": video_phash
        }).execute()

        upload_file(
            f"{user_id}/{proof_id}_enf.png",
            enf_png,
            "image/png"
        )

        return jsonify({
            "ok": True,
            "proof_id": proof_id
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

    finally:
        # ----------------------------
        # 5. CLEANUP
        # ----------------------------
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)

        ACTIVE_JOB = False


@app.route("/")
def health():
    return "OK", 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
