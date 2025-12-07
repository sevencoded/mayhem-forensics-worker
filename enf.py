import numpy as np
import librosa
import matplotlib.pyplot as plt
import io
import hashlib

def generate_enf_hash_and_image(filepath):
    y, sr = librosa.load(filepath, sr=4000)
    spec = np.abs(librosa.stft(y, n_fft=256))

    h = hashlib.sha256(spec.tobytes()).hexdigest()

    fig, ax = plt.subplots(figsize=(6,2))
    ax.imshow(20*np.log10(spec+1e-6), aspect='auto', origin='lower')
    ax.axis("off")

    buf = io.BytesIO()
    plt.savefig(buf, format="png", bbox_inches='tight', pad_inches=0)
    plt.close(fig)
    return h, buf.getvalue()
