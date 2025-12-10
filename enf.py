import uuid
import numpy as np
import librosa
import matplotlib.pyplot as plt
import io
import hashlib

def extract_enf(video_path):
    # 1) Audio load
    y, sr = librosa.load(video_path, sr=4000)

    # 2) STFT
    spec = np.abs(librosa.stft(y, n_fft=256))

    # 3) Hash
    enf_hash = hashlib.sha256(spec.tobytes()).hexdigest()

    # 4) PNG generacija
    fig, ax = plt.subplots(figsize=(6,2))
    ax.imshow(20*np.log10(spec + 1e-6), aspect="auto", origin="lower")
    ax.axis("off")

    buf = io.BytesIO()
    plt.savefig(buf, format="png", bbox_inches='tight', pad_inches=0)
    plt.close(fig)

    return enf_hash, buf.getvalue()
