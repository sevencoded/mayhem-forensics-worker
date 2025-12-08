import os
import traceback
from flask import Flask, request, jsonify
from supabase import create_client
import uuid
import tempfile
import time

from enf import generate_enf_hash_and_image
from audio_fp import generate_audio_fingerprint
from phash import generate_video_phash
from utils import upload_file

# -------------------------------------------------------
# INIT
# -------------------------------------------------------

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

app = Flask(__name__)

MAX_RETRIES = 3


# -------------------------------------------------------
# Helper: process video file
# -------------------------------------------------------

def process_video(local_path, user_id, name, sha256):
    """
    Returns dict of forensic data.
    """

    # === FORENSIC PROCESSING ===
    enf_hash, enf_image_bytes = generate_enf_hash_and_image(local_path)
    audio_fp = generate_audio_fingerprint(local_path)
    video_phash = generate_video_phash(local_path)

    # === UPLOAD ENF PNG ===
    proof_id = str(uuid.uuid4())
    enf_filename = f"{user_id}_{proof_id}_enf.png"

    upload_file(f"enf/{enf_filename}", enf_image_bytes, "image/png")

    # === INSERT PROOF ===
    proof_insert = supabase.table("proofs").insert({
        "id": proof_id,
        "user_id": user_id,
        "name": name,
        "hash": sha256,
        "signature": str(uuid.uuid4()),
        "witness_path": None   # intro mozemo dodati kasnije
    }).execute()

    # === INSERT FORENSIC RESULTS ===
    supabase.table("forensic_results").insert({
        "proof_id": proof_id,
        "enf_hash": enf_hash,
        "audio_fingerprint": audio_fp,
        "video_phash": video_phash,
        "metadata_hash": None,
        "chain_hash": None
    }).execute()

    return {
        "proof_id": proof_id,
        "enf_hash": enf_hash,
        "audio_fp": audio_fp,
        "video_phash": video_phash
    }


# -------------------------------------------------------
# /upload endpoint — PRIMA VIDEO DIREKTNO IZ FLUTTERA
# -------------------------------------------------------

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

        # TEMP SAVE VIDEO
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
        tmp.write(file.read())
        tmp.close()

        local_path = tmp.name

        # RETRY LOGIC
        for attempt in range(MAX_RETRIES):
            try:
                result = process_video(local_path, user_id, name, sha256)
                os.remove(local_path)
                return jsonify({
                    "ok": True,
                    "proof_id": result["proof_id"],
                    "forensic": result
                }), 200

            except Exception as e:
                print(f"Processing failed attempt {attempt+1}: {e}")
                traceback.print_exc()
                time.sleep(1)

        # FINAL FAIL
        os.remove(local_path)
        return jsonify({"ok": False, "status": "failed"}), 500

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


# -------------------------------------------------------
# START
# -------------------------------------------------------

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port)
