# This is commented code it for experiment, 

# import os
# import json
# from groq import Groq
# from dotenv import load_dotenv
# from search import vector_search
# from db import country_table_exists, get_extended_codes

# load_dotenv()

# groq_client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

# # ----------------------------
# # Scoring Helpers
# # ----------------------------
# def compute_score(llm_confidence, vector_score, hs_code, query, description):
#     # Signal 1: LLM confidence (70%) — matches main.py
#     llm_score = (llm_confidence / 100) * 0.70

#     # Signal 2: Vector similarity (20%) — restored from main.py
#     vec_score = vector_score * 0.20

#     # Signal 3: Code specificity bonus (10%) — fixed typo 0.01 → 0.10
#     code_len = len(str(hs_code).replace(".", "").strip())
#     if code_len >= 10:
#         specificity = 1.0
#     elif code_len == 8:
#         specificity = 0.7
#     else:
#         specificity = 0.4
#     spec_score = specificity * 0.10  # ← was 0.01, typo fixed

#     # Signal 4: Word overlap between query and description (10%)
#     query_words = set(query.lower().split())
#     desc_words = set(description.lower().split())
#     overlap = len(query_words & desc_words) / max(len(query_words), 1)
#     overlap_score = min(overlap, 1.0) * 0.10

#     final = (llm_score + vec_score + spec_score + overlap_score) * 100
#     return round(final, 1)

# def score_label(score):
#     if score >= 80:
#         return "HIGH CONFIDENCE"
#     elif score >= 60:
#         return "GOOD MATCH"
#     elif score >= 40:
#         return "POSSIBLE MATCH"
#     else:
#         return "LOW CONFIDENCE"

# # ----------------------------
# # Core Pipeline
# # ----------------------------
# def run_pipeline(country_code: str, product: str) -> dict:
#     country_code = country_code.strip().lower()

#     # Step 1: Vector search
#     six_digit_results, score_map = vector_search(product, top_k=5)
#     six_digit_codes = [r["hs_code"] for r in six_digit_results]

#     if not six_digit_codes:
#         raise ValueError(f"No vector search results found for product: '{product}'")

#     # Step 2: PostgreSQL lookup
#     if country_table_exists(country_code):
#         grouped_extended = get_extended_codes(country_code, six_digit_codes)

#         if not grouped_extended:
#             # Fallback: no extended codes found, use 6-digit results directly
#             print(f"[WARN] Country table exists for '{country_code}' but no extended codes matched. Falling back to 6-digit codes.")
#             use_extended = False
#         else:
#             use_extended = True

#         if use_extended:
#             context_parts = []
#             for six_digit, extended_rows in grouped_extended.items():
#                 parent = next(
#                     (r for r in six_digit_results if r["hs_code"].replace(".", "")[:6] == six_digit),
#                     None
#                 )
#                 parent_desc = parent["description"] if parent else ""
#                 context_parts.append(
#                     f"--- 6-Digit Code: {six_digit} | {parent_desc} ---"
#                 )
#                 for row in extended_rows:
#                     context_parts.append(
#                         f"  Full HS Code : {row['hs_code']}\n"
#                         f"  Description  : {row['description']}"
#                     )

#             system_prompt = (
#                 f"You are an HS Code classification expert. "
#                 f"The user is importing '{product}' into {country_code.upper()}. "
#                 "You are given extended HS codes grouped under their 6-digit parent. "
#                 "Pick the TOP 4 most relevant COMPLETE HS codes for this specific product. "
#                 "Only use codes from the provided context. "
#                 "Respond ONLY with a valid JSON array, no explanation, no markdown, no backticks. "
#                 'Format: [{"hs_code": "...", "description": "...", "reason": "...", "confidence": 90}, ...]'
#             )
#         else:
#             # Fallback path reuses 6-digit logic below
#             grouped_extended = None

#     if not country_table_exists(country_code) or not grouped_extended:
#         context_parts = []
#         for r in six_digit_results:
#             context_parts.append(
#                 f"HS Code    : {r['hs_code']}\n"
#                 f"Description: {r['description']}\n"
#                 f"Score      : {r['score']}"
#             )

#         system_prompt = (
#             f"You are an HS Code classification expert. "
#             f"The user is importing '{product}' into {country_code.upper()}. "
#             "No country-specific extended data was found. Use global 6-digit HS codes. "
#             "Pick the TOP 4 most relevant HS codes for this product. "
#             "Only use codes from the provided context. "
#             "Respond ONLY with a valid JSON array, no explanation, no markdown, no backticks. "
#             'Format: [{"hs_code": "...", "description": "...", "reason": "...", "confidence": 90}, ...]'
#         )

#     context = "\n".join(context_parts)

#     # Step 3: LLM call
#     response = groq_client.chat.completions.create(
#         model="llama-3.3-70b-versatile",
#         messages=[
#             {"role": "system", "content": system_prompt},
#             {"role": "user", "content": (
#                 f"Product       : {product}\n"
#                 f"Import Country: {country_code.upper()}\n\n"
#                 f"Available HS Codes:\n{context}\n\n"
#                 "Return the top 4 most relevant complete HS codes."
#             )}
#         ],
#         temperature=0
#     )

#     # Step 4: Parse LLM response
#     raw = response.choices[0].message.content.strip()
#     raw = raw.replace("```json", "").replace("```", "").strip()

#     try:
#         llm_results = json.loads(raw)
#     except Exception as e:
#         raise ValueError(f"LLM returned invalid JSON: {e}\nRaw response: {raw}")

#     if not isinstance(llm_results, list) or len(llm_results) == 0:
#         raise ValueError(f"LLM returned unexpected structure: {llm_results}")

#     # Step 5: Score each result
#     scored_results = []
#     for result in llm_results:
#         hs = str(result["hs_code"])
#         desc = result.get("description", "")
#         reason = result.get("reason", "")
#         llm_conf = result.get("confidence", 70)

#         six_prefix = hs.replace(".", "").replace(" ", "")[:6]
#         vec_score = score_map.get(six_prefix, 0.5)

#         final_score = compute_score(llm_conf, vec_score, hs, product, desc)

#         scored_results.append({
#             "hs_code": hs,
#             "description": desc,
#             "reason": reason,
#             "score": final_score,
#             "confidence_label": score_label(final_score)
#         })

#     return {
#         "country_code": country_code.upper(),
#         "product": product,
#         "results": scored_results
#     }


import os
import json
from groq import Groq
from dotenv import load_dotenv
from search import vector_search
from db import country_table_exists, get_extended_codes

load_dotenv()

groq_client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

# ----------------------------
# Scoring Helpers
# ----------------------------
def compute_score(llm_confidence, vector_score, hs_code, query, description):
    # Signal 1: LLM confidence on FINAL full code (70%)
    llm_score = (llm_confidence / 100) * 0.70

    # Signal 2: LLM relevance score on 6-digit code (20%)
    vec_score = vector_score * 0.20

    # Signal 3: Code specificity bonus (10%)
    code_len = len(str(hs_code).replace(".", "").strip())
    if code_len >= 10:
        specificity = 1.0
    elif code_len == 8:
        specificity = 0.7
    else:
        specificity = 0.4
    spec_score = specificity * 0.10

    # Signal 4: Word overlap between query and description (10%)
    query_words = set(query.lower().split())
    desc_words = set(description.lower().split())
    overlap = len(query_words & desc_words) / max(len(query_words), 1)
    overlap_score = min(overlap, 1.0) * 0.10

    final = (llm_score + vec_score + spec_score + overlap_score) * 100
    return round(final, 1)

def score_label(score):
    if score >= 80:
        return "HIGH CONFIDENCE"
    elif score >= 60:
        return "GOOD MATCH"
    elif score >= 40:
        return "POSSIBLE MATCH"
    else:
        return "LOW CONFIDENCE"

# ----------------------------
# Stage 1: LLM scores 6-digit vector DB results for relevance (20% signal)
# ----------------------------
def score_six_digit_relevance(product: str, six_digit_results: list) -> dict:
    items = "\n".join(
        f"HS Code: {r['hs_code']} | Description: {r['description']}"
        for r in six_digit_results
    )

    system_prompt = (
        "You are an HS Code relevance scorer. "
        "Given a product query and a list of 6-digit HS codes with their descriptions, "
        "score how semantically relevant each description is to the product query, "
        "on a scale of 0-100 (100 = perfect match, 0 = completely unrelated). "
        "Respond ONLY with a valid JSON array, no explanation, no markdown, no backticks. "
        'Format: [{"hs_code": "...", "relevance_score": 85}, ...]'
    )

    response = groq_client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": (
                f"Product Query: {product}\n\n"
                f"6-Digit HS Codes:\n{items}"
            )}
        ],
        temperature=0,
        seed=42 
    )

    raw = response.choices[0].message.content.strip()
    raw = raw.replace("```json", "").replace("```", "").strip()

    try:
        parsed = json.loads(raw)
    except Exception as e:
        print(f"[WARN] Failed to parse relevance scoring response: {e}\nRaw: {raw}")
        parsed = []

    relevance_map = {}
    if isinstance(parsed, list):
        for item in parsed:
            code = str(item.get("hs_code", "")).replace(".", "").replace(" ", "").strip()
            score = item.get("relevance_score", 50)
            if code:
                relevance_map[code[:6]] = score

    return relevance_map

# ----------------------------
# Core Pipeline
# ----------------------------
def run_pipeline(country_code: str, product: str) -> dict:
    country_code = country_code.strip().lower()

    # Step 1: Vector search (6-digit codes from vector DB)
    six_digit_results, score_map = vector_search(product, top_k=5)
    six_digit_codes = [r["hs_code"] for r in six_digit_results]

    if not six_digit_codes:
        raise ValueError(f"No vector search results found for product: '{product}'")

    # Step 1.5: LLM scores relevance of each 6-digit result against the query (20% signal)
    relevance_map = score_six_digit_relevance(product, six_digit_results)

    # Step 2: PostgreSQL lookup
    if country_table_exists(country_code):
        grouped_extended = get_extended_codes(country_code, six_digit_codes)

        if not grouped_extended:
            # Fallback: no extended codes found, use 6-digit results directly
            print(f"[WARN] Country table exists for '{country_code}' but no extended codes matched. Falling back to 6-digit codes.")
            use_extended = False
        else:
            use_extended = True

        if use_extended:
            context_parts = []
            for six_digit, extended_rows in grouped_extended.items():
                parent = next(
                    (r for r in six_digit_results if r["hs_code"].replace(".", "")[:6] == six_digit),
                    None
                )
                parent_desc = parent["description"] if parent else ""
                context_parts.append(
                    f"--- 6-Digit Code: {six_digit} | {parent_desc} ---"
                )
                for row in extended_rows:
                    context_parts.append(
                        f"  Full HS Code : {row['hs_code']}\n"
                        f"  Description  : {row['description']}"
                    )

            system_prompt = (
                f"You are an HS Code classification expert. "
                f"The user is importing '{product}' into {country_code.upper()}. "
                "You are given extended HS codes grouped under their 6-digit parent. "
                "Pick the TOP 4 most relevant COMPLETE HS codes for this specific product. "
                "Only use codes from the provided context. "
                "Respond ONLY with a valid JSON array, no explanation, no markdown, no backticks. "
                'Format: [{"hs_code": "...", "description": "...", "reason": "...", "confidence": 90}, ...]'
            )
        else:
            # Fallback path reuses 6-digit logic below
            grouped_extended = None

    if not country_table_exists(country_code) or not grouped_extended:
        context_parts = []
        for r in six_digit_results:
            context_parts.append(
                f"HS Code    : {r['hs_code']}\n"
                f"Description: {r['description']}\n"
                f"Score      : {r['score']}"
            )

        system_prompt = (
            f"You are an HS Code classification expert. "
            f"The user is importing '{product}' into {country_code.upper()}. "
            "No country-specific extended data was found. Use global 6-digit HS codes. "
            "Pick the TOP 4 most relevant HS codes for this product. "
            "Only use codes from the provided context. "
            "Respond ONLY with a valid JSON array, no explanation, no markdown, no backticks. "
            'Format: [{"hs_code": "...", "description": "...", "reason": "...", "confidence": 90}, ...]'
        )

    context = "\n".join(context_parts)

    # Step 3: LLM call — final full HS code selection (70% signal)
    response = groq_client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": (
                f"Product       : {product}\n"
                f"Import Country: {country_code.upper()}\n\n"
                f"Available HS Codes:\n{context}\n\n"
                "Return the top 4 most relevant complete HS codes."
            )}
        ],
        temperature=0
    )

    # Step 4: Parse LLM response
    raw = response.choices[0].message.content.strip()
    raw = raw.replace("```json", "").replace("```", "").strip()

    try:
        llm_results = json.loads(raw)
    except Exception as e:
        raise ValueError(f"LLM returned invalid JSON: {e}\nRaw response: {raw}")

    if not isinstance(llm_results, list) or len(llm_results) == 0:
        raise ValueError(f"LLM returned unexpected structure: {llm_results}")

    # Step 5: Score each result
    scored_results = []
    for result in llm_results:
        hs = str(result["hs_code"])
        desc = result.get("description", "")
        reason = result.get("reason", "")
        llm_conf = result.get("confidence", 70)  # 70% signal, from final code selection

        six_prefix = hs.replace(".", "").replace(" ", "")[:6]
        relevance_score = relevance_map.get(six_prefix, 50)  # 20% signal, from stage 1
        vec_score = relevance_score / 100  # normalize to 0-1

        final_score = compute_score(llm_conf, vec_score, hs, product, desc)

        scored_results.append({
            "hs_code": hs,
            "description": desc,
            "reason": reason,
            "score": final_score,
            "confidence_label": score_label(final_score)
        })

    return {
        "country_code": country_code.upper(),
        "product": product,
        "results": scored_results
    }