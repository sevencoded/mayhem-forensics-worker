import os
import asyncio
import tempfile
from supabase import create_client
import requests
import soundfile as sf
import numpy as np

from processing.enf import extract_enf
from processing.audio_fp import extract_audio_fingerprint
from processing.phash import extract_video_phash
from processing.utils import save_spectrogram_png

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

async def process_job(job):
    proof_id = job["proof_id"]
    video_path = job["video_path"]
    user_id = job["user_id"]

    print("🔵 Processing", proof_id)

    # 1) Download video from bucket
    main_bucket = "main_videos"

    resp = supabase.storage.from_(main_bucket).download(video_path)
    data = resp

    # Save temp file
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
    tmp.write(data)
    tmp.close()
    video_file = tmp.name

    # Extract audio
    audio, sr = sf.read(video_file)

    # =============== ENF ==================
    enf_hash, enf_conf, spect = extract_enf(audio, sr)

    spect_file = None
    if spect is not None:
        spect_file = f"{user_id}_{proof_id}_enf.png"
        save_spectrogram_png(spect, spect_file)

        # Upload spectrogram
        supabase.storage.from_("main_videos").upload(
            f"enf/{spect_file}",
            open(spect_file, "rb"),
            {"content-type": "image/png"}
        )

    # ============== AUDIO FINGERPRINT ==============
    audio_fp = extract_audio_fingerprint(audio, sr)

    # ============== VIDEO PHASH ==============
    phash = extract_video_phash(video_file)

    # Insert forensic results
    supabase.table("forensic_results").insert({
        "proof_id": proof_id,
        "enf_hash": enf_hash,
        "audio_fingerprint": audio_fp,
        "video_phash": phash,
        "metadata_hash": None,
        "chain_hash": None
    }).execute()

    # Mark job done
    supabase.table("forensic_queue").update({"status": "done"}).eq("id", job["id"]).execute()

    # Delete video from bucket
    supabase.storage.from_(main_bucket).remove([video_path])

    print("✔ Done", proof_id)

async def loop():
    while True:
        jobs = supabase.table("forensic_queue").select("*").eq("status", "pending").execute().data

        for job in jobs:
            await process_job(job)

        await asyncio.sleep(10)

if __name__ == "__main__":
    asyncio.run(loop())
