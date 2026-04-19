import pandas as pd
import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression

# Load training data
df = pd.read_csv("home/thane_crime_data.csv")  
# columns: text,label

X = df["text"]
y = df["label"]

vectorizer = TfidfVectorizer(stop_words="english", max_features=5000)
X_vec = vectorizer.fit_transform(X)

model = LogisticRegression(max_iter=1000)
model.fit(X_vec, y)

joblib.dump(model, "crime_classifier.pkl")
joblib.dump(vectorizer, "vectorizer.pkl")

print("Model trained & saved")
