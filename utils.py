import numpy as np
import io
from PIL import Image
import matplotlib.pyplot as plt

def save_spectrogram_png(S, out_path):
    plt.figure(figsize=(10, 4))
    plt.imshow(S, aspect='auto', origin='lower')
    plt.colorbar()
    plt.tight_layout()
    plt.savefig(out_path, dpi=140)
    plt.close()

def sha256_bytes(data: bytes):
    import hashlib
    return hashlib.sha256(data).hexdigest()
