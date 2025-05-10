from fastapi import APIRouter, Form
from typing import Optional
from app.utils.semantic_search import (
    determine_query_type,
    search_similar_items,
    generate_answer_with_context,
    generate_combined_answer_with_context,
    filter_relevant_items_with_llm,
    enhance_query_with_personal_context,
)
from app.utils.chat_vector_store import save_chat_vector_to_pinecone
import json, time

router = APIRouter()


@router.post("/search/")
async def search(
    user_id: str = Form(...),
    query: str = Form(...),
    top_k_photo: Optional[int] = Form(10),
    top_k_info: Optional[int] = Form(10),
):
    timestamp = int(time.time())

    # 사용자 쿼리 저장
    save_chat_vector_to_pinecone(user_id, "user", query, timestamp)

    enhanced_query = enhance_query_with_personal_context(user_id, query)

    # 벡터 검색
    raw_info_results = search_similar_items(user_id, enhanced_query, "info", top_k_info)
    raw_photo_results = search_similar_items(
        user_id, enhanced_query, "photo", top_k_photo
    )

    # LLM 필터링
    info_results = filter_relevant_items_with_llm(
        enhanced_query, raw_info_results, "정보"
    )
    photo_results = filter_relevant_items_with_llm(
        enhanced_query, raw_photo_results, "사진"
    )

    # 통합 답변 생성
    result = generate_combined_answer_with_context(
        user_id, enhanced_query, info_results, photo_results
    )

    # 응답 저장
    serialized_result = json.dumps(result, ensure_ascii=False)
    save_chat_vector_to_pinecone(
        user_id, "assistant", serialized_result, int(time.time())
    )

    return result
