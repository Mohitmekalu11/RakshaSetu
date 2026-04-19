import cv2
from PIL import Image
import torch
import numpy as np
from transformers import AutoImageProcessor, AutoModelForImageClassification
from facenet_pytorch import MTCNN

# 1. Load deepfake model
model_name = "prithivMLmods/deepfake-detector-model-v1"
processor = AutoImageProcessor.from_pretrained(model_name)
model = AutoModelForImageClassification.from_pretrained(model_name)

# 2. Initialize face detector (MTCNN)
mtcnn = MTCNN(keep_all=True, device='cpu')  # CPU-friendly

# 3. Function to detect deepfake in video
def detect_deepfake_video(video_path, frame_skip=10):
    cap = cv2.VideoCapture(video_path)
    frame_count = 0
    fake_probs = []

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        # Only process every Nth frame
        if frame_count % frame_skip == 0:
            # Convert frame to PIL image
            image = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            
            # Detect faces
            faces = mtcnn(image)
            
            if faces is not None:
                for face in faces:
                    # MTCNN returns tensors; convert to PIL
                    face_image = Image.fromarray((face.permute(1,2,0).numpy() * 255).astype(np.uint8))
                    
                    # Preprocess & predict
                    inputs = processor(images=face_image, return_tensors="pt")
                    with torch.no_grad():
                        outputs = model(**inputs)
                        probs = torch.nn.functional.softmax(outputs.logits, dim=-1)
                        fake_prob = probs[0][1].item()  # index 1 = FAKE
                        fake_probs.append(fake_prob)

        frame_count += 1

    cap.release()

    if fake_probs:
        avg_fake_prob = np.mean(fake_probs)
        verdict = "FAKE" if avg_fake_prob > 0.5 else "REAL"
        return verdict, round(avg_fake_prob * 100, 2)
    else:
        return "UNKNOWN", 0

# 4. Test with a video
if __name__ == "__main__":
    video_path = "deepfake_videos/ai_crimeVideo.mp4"  # replace with your video path
    verdict, confidence = detect_deepfake_video(video_path)
    print(f"Verdict: {verdict} ({confidence}% confidence)")
