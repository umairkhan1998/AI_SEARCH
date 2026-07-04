# AI_SEARCH

AI_SEARCH is a prototype HS Code classification service that combines vector search with LLM scoring.

It uses:
- FastAPI for the API layer
- ChromaDB for vector search
- SentenceTransformers for embeddings
- Groq LLM for HS code relevance and selection
- Excel input data for HS code descriptions

## Project Structure

- `app.py` - FastAPI application exposing classification endpoints
- `pipeline.py` - business logic for vector search, country-specific lookup, and LLM scoring
- `search.py` - ChromaDB query wrapper and embedding lookup
- `vectordb.py` - ingestion script to build/store embeddings from Excel data
- `db.py` - country-specific HS code lookup helpers
- `requirements.txt` - Python dependencies
- `data/` - source files used for ingestion
- `hs_vector_db/` - local ChromaDB persistent store

## Requirements

Install dependencies from `requirements.txt`:

```bash
pip install -r requirements.txt
```

## Environment

Create a `.env` file with your Groq API key:

```env
GROQ_API_KEY=your_groq_api_key_here
```

## Setup and usage

1. Populate the vector store:
   - `vectordb.py` reads `data/ai_Search_six_digit.xlsx`
   - It creates embeddings and writes them into `hs_vector_db`

2. Start the API server:

```bash
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

3. Use the API endpoints:
   - `POST /classify` for a single product classification
   - `POST /classify/batch` for up to 10 product queries at once

## Example request

```json
POST /classify
{
  "country_code": "us",
  "product": "electric bicycle battery"
}
```

## Chunk size control

If you need chunking, update `vectordb.py` during ingestion. The file is where the document is split and embedded, so `chunk_size` and `chunk_overlap` are controlled there.

## Notes

- The service currently assumes the vector database is built from the Excel file.
- `pipeline.py` executes the final LLM classification and result scoring.
- You can customize prompt or scoring behavior inside `pipeline.py`.

## Contact

This repository is intended for experimentation and proof-of-concept HS code classification.

