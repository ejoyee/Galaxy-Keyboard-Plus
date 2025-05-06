from fastapi import APIRouter, Form
from app.utils.semantic_search import (
    determine_query_type,
    search_similar_items,
    generate_answer_from_info,
)

router = APIRouter()


@router.post("/search/")
async def search(user_id: str = Form(...), query: str = Form(...)):
    query_type = determine_query_type(query)

    result = {"query_type": query_type}

    if query_type == "photo":
        photo_results = search_similar_items(user_id, query, "photo")
        result["photo_results"] = photo_results
    elif query_type == "info":
        info_results = search_similar_items(user_id, query, "info")
        result["answer"] = generate_answer_from_info(query, info_results)
        result["info_results"] = info_results
    else:  # ambiguous
        photo_results = search_similar_items(user_id, query, "photo")
        info_results = search_similar_items(user_id, query, "info")
        result["photo_results"] = photo_results
        result["answer"] = generate_answer_from_info(query, info_results)
        result["info_results"] = info_results

    return result
