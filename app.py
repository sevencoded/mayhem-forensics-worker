import os
os.environ["MPLCONFIGDIR"] = "/tmp/matplotlib"

import asyncio
import tempfile
import subprocess
import soundfile as sf

from supabase import create_client
from enf import extract_enf
from audio_fp import extract_audio_fingerprint
from phash import extract_video_phash
from utils import save_spectrogram_png

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
MAIN_BUCKET = "main_videos"

def convert_to_wav(in_path):
    out_path = tempfile.NamedTemporaryFile(delete=False, suffix=".wav").name
    cmd = ["ffmpeg", "-y", "-i", in_path, "-t", "5", "-vn", "-ac", "1", "-ar", "16000", out_path]
    try:
        subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        return out_path
    except:
        return None

async def process_job(job):
    proof_id = job["proof_id"]
    video_path = job["video_path"]
    user_id = job["user_id"]

    print("Processing:", proof_id)

    try:
        data = supabase.storage.from_(MAIN_BUCKET).download(video_path)
    except Exception as e:
        print("Download error:", e)
        return

    tmp_mp4 = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
    tmp_mp4.write(data)
    tmp_mp4.close()

    wav_path = convert_to_wav(tmp_mp4.name)
    if not wav_path:
        return

    audio, sr = sf.read(wav_path)

    enf_hash, conf, spect = extract_enf(audio, sr)
    fp = extract_audio_fingerprint(audio, sr)
    phash = extract_video_phash(tmp_mp4.name)

    # upload ENF PNG
    spect_name = f"{user_id}_{proof_id}_enf.png"
    save_spectrogram_png(spect, spect_name)

    supabase.storage.from_(MAIN_BUCKET).upload(
        f"enf/{spect_name}",
        open(spect_name, "rb"),
        {"content-type": "image/png"},
    )

    # save forensic
    supabase.table("forensic_results").insert({
        "proof_id": proof_id,
        "enf_hash": enf_hash,
        "audio_fingerprint": fp,
        "video_phash": phash
    }).execute()

    # delete original video
    supabase.storage.from_(MAIN_BUCKET).remove([video_path])

    os.remove(tmp_mp4.name)
    os.remove(wav_path)
    os.remove(spect_name)

    supabase.table("forensic_queue").update({"status": "done"}).eq("id", job["id"]).execute()

async def loop():
    print("Worker ready.")
    while True:
        jobs = supabase.table("forensic_queue").select("*").eq("status", "pending").execute().data
        if jobs:
            for j in jobs:
                await process_job(j)
        await asyncio.sleep(5)

asyncio.run(loop())
