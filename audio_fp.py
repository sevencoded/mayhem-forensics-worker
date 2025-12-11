import hashlib
import numpy as np
import librosa

def extract_audio_fingerprint(path: str) -> str:
    y, sr = librosa.load(path, sr=11025, mono=True, duration=60.0)
    if y.size == 0:
        raise ValueError("Empty audio")

    S = librosa.feature.melspectrogram(
        y=y, sr=sr, n_fft=2048, hop_length=512,
        n_mels=64, power=2.0
    )
    S_db = librosa.power_to_db(S + 1e-9, ref=np.max)

    descriptor = S_db.mean(axis=1).astype(np.float32)
    descriptor -= descriptor.mean()
    std = descriptor.std() or 1.0
    descriptor /= std

    return hashlib.sha256(descriptor.tobytes()).hexdigest()
