import chromadb
from sentence_transformers import SentenceTransformer

model = SentenceTransformer(
    "nomic-ai/nomic-embed-text-v1.5",
    trust_remote_code=True
)

chroma_client = chromadb.PersistentClient(path="./hs_vector_db")
collection = chroma_client.get_collection("hs_codes")

def vector_search(query: str, top_k: int = 5) -> list[dict]:
    """Search ChromaDB and return top matching 6-digit HS codes."""
    embedding = model.encode(query, normalize_embeddings=True)

    results = collection.query(
        query_embeddings=[embedding.tolist()],
        n_results=top_k
    )

    # matches = []
    # for metadata, distance in zip(results["metadatas"][0], results["distances"][0]):
    #     matches.append({
    #         "hs_code": metadata["hs_code"],
    #         "description": metadata["description"],
    #         "score": round(1 - distance, 4)
    #     })

    matches = []
    score_map = {}

    for metadata, distance in zip(results["metadatas"][0], results["distances"][0]):
        hs_code = metadata["hs_code"]
        score = round(1 - distance, 4)

        matches.append({
            "hs_code": hs_code,
            "description": metadata["description"],
            "score": score
        })

        # Keyed by clean 6-digit code for easy lookup in main.py
        clean_code = hs_code.replace(".", "").replace(" ", "")[:6]
        score_map[clean_code] = score

    return matches, score_map    

    return matches