import os
os.environ["MPLCONFIGDIR"] = "/tmp/matplotlib"   # Render fix za Matplotlib

import asyncio
import tempfile
import subprocess
import numpy as np
import soundfile as sf

from supabase import create_client

from enf import extract_enf
from audio_fp import extract_audio_fingerprint
from phash import extract_video_phash
from utils import save_spectrogram_png


# ENV
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
MAIN_BUCKET = "main_videos"


def convert_to_wav(in_path):
    out_path = tempfile.NamedTemporaryFile(delete=False, suffix=".wav").name

    cmd = [
        "ffmpeg", "-y",
        "-i", in_path,
        "-t", "12",
        "-vn",
        "-ac", "1",
        "-ar", "16000",
        out_path
    ]

    try:
        subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        return out_path
    except Exception as e:
        print("FFmpeg error:", e)
        return None


async def process_job(job):
    proof_id = job["proof_id"]
    video_path = job["video_path"]
    user_id = job["user_id"]

    print("🔵 Processing:", proof_id)

    # DOWNLOAD VIDEO
    try:
        data = supabase.storage.from_(MAIN_BUCKET).download(video_path)
    except Exception as e:
        print("❌ download error:", e)
        return

    tmp_mp4 = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
    tmp_mp4.write(data)
    tmp_mp4.close()

    # WAV
    wav_path = convert_to_wav(tmp_mp4.name)
    if wav_path is None:
        print("❌ wav conversion failed")
        return

    try:
        audio, sr = sf.read(wav_path)
    except Exception as e:
        print("❌ load wav failed:", e)
        return

    # FEATURES
    enf_hash, enf_conf, spect = extract_enf(audio, sr)
    audio_fp = extract_audio_fingerprint(audio, sr)
    phash = extract_video_phash(tmp_mp4.name)

    # SPECTROGRAM
    spect_name = None
    if spect is not None:
        spect_name = f"{user_id}_{proof_id}_enf.png"
        save_spectrogram_png(spect, spect_name)

        try:
            supabase.storage.from_(MAIN_BUCKET).upload(
                f"enf/{spect_name}",
                open(spect_name, "rb"),
                {"content-type": "image/png"}
            )
        except:
            pass

    # SAVE RESULT
    supabase.table("forensic_results").insert({
        "proof_id": proof_id,
        "enf_hash": enf_hash,
        "audio_fingerprint": audio_fp,
        "video_phash": phash,
        "metadata_hash": None,
        "chain_hash": None
    }).execute()

    supabase.table("forensic_queue").update({"status": "done"}).eq("id", job["id"]).execute()

    # DELETE TEMP FILES
    os.remove(tmp_mp4.name)
    if os.path.exists(wav_path):
        os.remove(wav_path)
    if spect_name and os.path.exists(spect_name):
        os.remove(spect_name)

    print("✔ DONE:", proof_id)


async def loop():
    print("🚀 Worker online.")
    while True:
        try:
            jobs = supabase.table("forensic_queue").select("*").eq("status", "pending").execute().data
        except Exception as e:
            print("❌ queue select error:", e)
            await asyncio.sleep(5)
            continue

        if not jobs:
            print("⏳ No jobs...")
        else:
            print(f"📌 Found {len(jobs)} job(s).")

        for j in jobs:
            await process_job(j)

        await asyncio.sleep(5)


# RENDER FIX — uvek pokreni loop, bez __main__
asyncio.run(loop())
