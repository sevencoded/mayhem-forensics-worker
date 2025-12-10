import uuid
import numpy as np

def extract_enf(video_path):
    enf_hash = uuid.uuid4().hex
    png = b"\x89PNG SIMULATED"
    return enf_hash, png
