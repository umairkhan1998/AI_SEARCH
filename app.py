import asyncio
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List
from pipeline import run_pipeline

app = FastAPI()

class HSRequest(BaseModel):
    country_code: str
    product: str

class HSResult(BaseModel):
    hs_code: str
    description: str
    reason: str
    score: float
    confidence_label: str

class HSResponse(BaseModel):
    country_code: str
    product: str
    results: List[HSResult]

class BatchHSRequest(BaseModel):
    queries: List[HSRequest]

class BatchHSResponse(BaseModel):
    responses: List[HSResponse]


@app.post("/classify", response_model=HSResponse)
async def classify_single(request: HSRequest):
    """Classify a single product for a given import country."""
    try:
        # Use get_running_loop() — correct for Python 3.10+
        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(
            None,
            lambda: run_pipeline(request.country_code, request.product)
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Pipeline error: {str(e)}")

@app.post("/classify/batch", response_model=BatchHSResponse)
async def classify_batch(request: BatchHSRequest):
    """Classify multiple products in parallel."""
    if len(request.queries) > 10:
        raise HTTPException(
            status_code=400,
            detail="Batch limit is 10 queries per request"
        )
    try:
        loop = asyncio.get_running_loop()
        tasks = [
            loop.run_in_executor(
                None,
                lambda q=q: run_pipeline(q.country_code, q.product)
            )
            for q in request.queries
        ]
        responses = await asyncio.gather(*tasks, return_exceptions=True)

        # Surface any per-task errors instead of silently swallowing them
        results = []
        for i, resp in enumerate(responses):
            if isinstance(resp, Exception):
                raise HTTPException(
                    status_code=500,
                    detail=f"Query {i+1} failed: {str(resp)}"
                )
            results.append(resp)

        return BatchHSResponse(responses=results)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Batch pipeline error: {str(e)}")

# import asyncio
# from fastapi import FastAPI, HTTPException
# from pydantic import BaseModel
# from typing import List
# from pipeline import run_pipeline

# app = FastAPI(
#     title="HS Code Classification API",
#     description="RAG-based HS Code classifier using ChromaDB + PostgreSQL + Groq LLM",
#     version="2.0.0"
# )


# class HSRequest(BaseModel):
#     country_code: str
#     product: str

# class HSResult(BaseModel):
#     hs_code: str
#     description: str
#     reason: str
#     score: float
#     confidence_label: str

# class HSResponse(BaseModel):
#     country_code: str
#     product: str
#     results: List[HSResult]

# class BatchHSRequest(BaseModel):
#     queries: List[HSRequest]

# class BatchHSResponse(BaseModel):
#     responses: List[HSResponse]

# # ----------------------------
# # Endpoints
# # ----------------------------
# @app.get("/")
# def root():
#     return {
#         "message": "HS Code Classification API is running",
#         "endpoints": {
#             "single": "POST /classify",
#             "batch" : "POST /classify/batch",
#             "docs"  : "GET  /docs"
#         }
#     }

# @app.post("/classify", response_model=HSResponse)
# async def classify_single(request: HSRequest):
#     """Classify a single product for a given import country."""
#     try:
#         loop = asyncio.get_event_loop()
#         result = await loop.run_in_executor(
#             None,
#             lambda: run_pipeline(request.country_code, request.product)
#         )
#         return result
#     except ValueError as e:
#         raise HTTPException(status_code=500, detail=str(e))
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Pipeline error: {str(e)}")

# @app.post("/classify/batch", response_model=BatchHSResponse)
# async def classify_batch(request: BatchHSRequest):
#     """Classify multiple products in parallel."""
#     if len(request.queries) > 10:
#         raise HTTPException(
#             status_code=400,
#             detail="Batch limit is 10 queries per request"
#         )
#     try:
#         loop = asyncio.get_event_loop()
#         tasks = [
#             loop.run_in_executor(
#                 None,
#                 lambda q=q: run_pipeline(q.country_code, q.product)
#             )
#             for q in request.queries
#         ]
#         responses = await asyncio.gather(*tasks)
#         return BatchHSResponse(responses=list(responses))
#     except ValueError as e:
#         raise HTTPException(status_code=500, detail=str(e))
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Pipeline error: {str(e)}")