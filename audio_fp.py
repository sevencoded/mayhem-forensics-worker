import numpy as np
import librosa
from utils import sha256_bytes

def extract_audio_fingerprint(audio_data, sample_rate):
    if audio_data is None or len(audio_data) < sample_rate * 0.5:
        return None

    try:
        mfcc = librosa.feature.mfcc(
            y=audio_data.astype(np.float32),
            sr=sample_rate,
            n_mfcc=20
        )
    except:
        return None

    reduced = np.mean(mfcc, axis=1).astype(np.float32)
    return sha256_bytes(reduced.tobytes())
