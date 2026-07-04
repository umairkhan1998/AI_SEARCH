import pandas as pd
import chromadb
from sentence_transformers import SentenceTransformer

model = SentenceTransformer(
    "nomic-ai/nomic-embed-text-v1.5",
    trust_remote_code=True
)

client = chromadb.PersistentClient(path="./hs_vector_db")
collection = client.get_or_create_collection(name="hs_codes")

# Fix: use raw string or forward slashes for path
df = pd.read_excel(r"C:\Users\Umair Khan\Desktop\ai_search\data\ai_Search_six_digit.xlsx")

for _, row in df.iterrows():
    hs_code = str(row["hscode"]).strip()
    description = str(row["description"]).strip()

    document = f"HS Code: {hs_code}\nDescription: {description}"

    embedding = model.encode(document, normalize_embeddings=True)

    collection.add(
        ids=[hs_code],
        documents=[document],
        embeddings=[embedding.tolist()],
        metadatas=[{"hs_code": hs_code, "description": description}]
    )

print(f"Inserted {len(df)} records.")