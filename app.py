import os
import asyncio
import tempfile
import subprocess
import numpy as np

from supabase import create_client

# Forensics modules
from enf import extract_enf
from audio_fp import extract_audio_fingerprint
from phash import extract_video_phash
from utils import save_spectrogram_png

# Environment
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

MAIN_BUCKET = "main_videos"


# -------------------------------------------------------
# Convert MP4 → WAV using FFmpeg (100% reliable)
# -------------------------------------------------------
def convert_to_wav(input_path):
    out_wav = tempfile.NamedTemporaryFile(delete=False, suffix=".wav").name

    cmd = [
        "ffmpeg", "-y",
        "-i", input_path,
        "-vn",
        "-ac", "1",
        "-ar", "16000",
        out_wav
    ]

    try:
        subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        return out_wav
    except Exception as e:
        print("FFmpeg error:", e)
        return None


# -------------------------------------------------------
# MAIN FORENSIC PROCESS
# -------------------------------------------------------
async def process_job(job):
    proof_id = job["proof_id"]
    video_path = job["video_path"]
    user_id = job["user_id"]

    print("🔵 Processing job:", proof_id)

    # 1) Download video from bucket
    try:
        video_bytes = supabase.storage.from_(MAIN_BUCKET).download(video_path)
    except Exception as e:
        print("❌ Storage download failed:", e)
        supabase.table("forensic_queue").update({"status": "error"}).eq("id", job["id"]).execute()
        return

    # Save downloaded file
    tmp_mp4 = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
    tmp_mp4.write(video_bytes)
    tmp_mp4.close()

    # 2) Extract WAV using FFmpeg
    wav_path = convert_to_wav(tmp_mp4.name)
    if wav_path is None:
        print("❌ WAV conversion failed")
        supabase.table("forensic_queue").update({"status": "error"}).eq("id", job["id"]).execute()
        return

    # Load WAV audio manually
    try:
        import soundfile as sf
        audio, sr = sf.read(wav_path)
    except Exception as e:
        print("❌ Audio load failed:", e)
        supabase.table("forensic_queue").update({"status": "error"}).eq("id", job["id"]).execute()
        return

    # ------------------ ENF ------------------
    enf_hash, enf_conf, spect = extract_enf(audio, sr)

    spect_filename = None
    if spect is not None:
        spect_filename = f"{user_id}_{proof_id}_enf.png"
        save_spectrogram_png(spect, spect_filename)

        # Upload ENF spectrogram
        try:
            supabase.storage.from_(MAIN_BUCKET).upload(
                f"enf/{spect_filename}",
                open(spect_filename, "rb"),
                {"content-type": "image/png"}
            )
        except Exception as e:
            print("⚠ Failed to upload spectrogram:", e)

    # ------------------ AUDIO FINGERPRINT ------------------
    audio_fp = extract_audio_fingerprint(audio, sr)

    # ------------------ VIDEO PHASH ------------------
    phash = extract_video_phash(tmp_mp4.name)

    # ------------------ SAVE RESULTS ------------------
    supabase.table("forensic_results").insert({
        "proof_id": proof_id,
        "enf_hash": enf_hash,
        "audio_fingerprint": audio_fp,
        "video_phash": phash,
        "metadata_hash": None,
        "chain_hash": None
    }).execute()

    # Mark job as complete
    supabase.table("forensic_queue").update({"status": "done"}).eq("id", job["id"]).execute()

    # Cleanup both files
    os.remove(tmp_mp4.name)
    if os.path.exists(wav_path):
        os.remove(wav_path)

    print("✔ Completed job:", proof_id)


# -------------------------------------------------------
# WORKER LOOP
# -------------------------------------------------------
async def loop():
    print("🚀 Worker started and is polling Supabase…")

    while True:
        try:
            jobs = supabase.table("forensic_queue").select("*").eq("status", "pending").execute().data
        except Exception as e:
            print("Supabase SELECT error:", e)
            await asyncio.sleep(5)
            continue

        for job in jobs:
            await process_job(job)

        await asyncio.sleep(10)


if __name__ == "__main__":
    asyncio.run(loop())
