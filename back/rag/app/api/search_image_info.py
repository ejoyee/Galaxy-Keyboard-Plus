from fastapi import APIRouter, Form
from typing import Optional
from app.utils.semantic_search import (
    determine_query_type,
    search_similar_items,
    generate_answer_from_info,
)

router = APIRouter()


@router.post("/search/")
async def search(
    user_id: str = Form(...),
    query: str = Form(...),
    top_k_photo: Optional[int] = Form(5),
    top_k_info: Optional[int] = Form(5),
):
    query_type = determine_query_type(query)
    result = {"query_type": query_type}

    if query_type == "photo":
        photo_results = search_similar_items(user_id, query, "photo", top_k_photo)
        result["photo_results"] = photo_results
    elif query_type == "info":
        info_results = search_similar_items(user_id, query, "info", top_k_info)
        result["answer"] = generate_answer_from_info(query, info_results)
        result["info_results"] = info_results
    else:  # ambiguous
        photo_results = search_similar_items(user_id, query, "photo", top_k_photo)
        info_results = search_similar_items(user_id, query, "info", top_k_info)
        result["photo_results"] = photo_results
        result["answer"] = generate_answer_from_info(query, info_results)
        result["info_results"] = info_results

    return result
