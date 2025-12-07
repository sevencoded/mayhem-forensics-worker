from PIL import Image
import imagehash
import cv2

def generate_video_phash(filepath):
    cap = cv2.VideoCapture(filepath)
    ret, frame = cap.read()
    cap.release()
    if not ret:
        return None
    img = Image.fromarray(frame)
    return str(imagehash.phash(img))
