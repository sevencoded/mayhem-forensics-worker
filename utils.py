import hashlib
import matplotlib.pyplot as plt

def sha256_bytes(data: bytes):
    return hashlib.sha256(data).hexdigest()

def save_spectrogram_png(S, out_path):
    plt.figure(figsize=(8, 3))
    plt.imshow(S, aspect='auto', origin='lower', cmap='inferno')
    plt.colorbar()
    plt.tight_layout()
    plt.savefig(out_path, dpi=120)
    plt.close()
