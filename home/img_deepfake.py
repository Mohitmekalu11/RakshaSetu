from transformers import AutoImageProcessor, AutoModelForImageClassification
from PIL import Image
import torch

# 1. Load model and processor
model_name = "prithivMLmods/deepfake-detector-model-v1"
processor = AutoImageProcessor.from_pretrained(model_name)
model = AutoModelForImageClassification.from_pretrained(model_name)

# 2. Load an image (replace with your test image path)
image_path = "deepfake_images/download.jpeg"
image = Image.open(image_path).convert("RGB")

# 3. Preprocess
inputs = processor(images=image, return_tensors="pt")

# 4. Run inference
with torch.no_grad():
    outputs = model(**inputs)
    logits = outputs.logits
    predicted_class = logits.argmax(-1).item()

# 5. Interpret result
labels = model.config.id2label
print(f"Predicted class: {labels[predicted_class]}")
