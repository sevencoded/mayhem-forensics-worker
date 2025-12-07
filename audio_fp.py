import numpy as np
import librosa
from .utils import sha256_bytes

def extract_audio_fingerprint(audio_data, sample_rate):
    mfcc = librosa.feature.mfcc(y=audio_data, sr=sample_rate, n_mfcc=20)
    flat = mfcc.flatten().tobytes()
    return sha256_bytes(flat)
