import os
import pickle

# Get absolute path of chatbot folder
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Path to ml folder
ML_PATH = os.path.join(BASE_DIR, "ml")

# Load model files once
model = pickle.load(open(os.path.join(ML_PATH, "intent_model.pkl"), "rb"))
vectorizer = pickle.load(open(os.path.join(ML_PATH, "vectorizer.pkl"), "rb"))
label_encoder = pickle.load(open(os.path.join(ML_PATH, "label_encoder.pkl"), "rb"))


def clean_text(text):
    return text.lower()


def predict_intent(text):
    text = clean_text(text)
    vec = vectorizer.transform([text])
    pred = model.predict(vec)
    return label_encoder.inverse_transform(pred)[0]
    severity_map = {
        "rape": 1.0,
        "sexual assault": 0.9,
        "assault": 0.8,
        "domestic violence": 0.8,
        "threat": 0.7,
        "stalking": 0.6,
        "harassment": 0.5,
        "verbal abuse": 0.4
    }

from .models import SeverityKeyword

def calculate_severity(text):
    text = text.lower()
    score = 0

    keywords = SeverityKeyword.objects.all()

    for item in keywords:
        if item.keyword.lower() in text:
            score = max(score, item.weight)

    return score

