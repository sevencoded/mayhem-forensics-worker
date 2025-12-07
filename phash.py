import cv2
import numpy as np
from utils import sha256_bytes

def extract_video_phash(video_path):
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        return None

    hashes = []
    frame_id = 0

    while True:
        ok, frame = cap.read()
        if not ok:
            break

        if frame_id % 20 != 0:
            frame_id += 1
            continue

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        small = cv2.resize(gray, (32, 32))

        dct = cv2.dct(np.float32(small))
        block = dct[:8, :8]

        hashes.append(
            sha256_bytes(block.flatten().astype(np.float32).tobytes())
        )
        frame_id += 1

    cap.release()

    if len(hashes) == 0:
        return None

    return sha256_bytes("|".join(hashes).encode())
