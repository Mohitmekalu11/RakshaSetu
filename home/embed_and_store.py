import os
import pandas as pd
import pickle
import faiss
import openai
import numpy as np
from dotenv import load_dotenv
import os

# this will read .env and put variables into os.environ
load_dotenv()



openai.api_key = os.getenv("OPENAI_API_KEY")

df = pd.read_csv("home/crime_data.csv")
records = df.to_dict(orient="records")
texts = [str(rec) for rec in records]

def get_embedding(text, model="text-embedding-ada-002"):
    resp = openai.Embedding.create(model=model, input=text)
    return resp["data"][0]["embedding"]

embs = [get_embedding(t) for t in texts]

d = len(embs[0])
index = faiss.IndexFlatL2(d)
index.add(np.array(embs, dtype="float32"))

faiss.write_index(index, "crime_index.faiss")
with open("crime_texts.pkl", "wb") as f:
    pickle.dump(records, f)

print("✅ Embeddings and FAISS index saved.")
