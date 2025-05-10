from fastapi import APIRouter, Form
from typing import Optional
from app.utils.semantic_search import (
    determine_query_type,
    search_similar_items,
    generate_answer_with_context,
    generate_combined_answer_with_context,
)
from app.utils.chat_vector_store import save_chat_vector_to_pinecone
import json, time

router = APIRouter()


@router.post("/search/")
async def search(
    user_id: str = Form(...),
    query: str = Form(...),
    top_k_photo: Optional[int] = Form(5),
    top_k_info: Optional[int] = Form(5),
):
    timestamp = int(time.time())

    # 사용자 질문 저장
    save_chat_vector_to_pinecone(user_id, "user", query, timestamp)

    # info + photo 모두 검색
    info_results = search_similar_items(user_id, query, "info", top_k_info)
    photo_results = search_similar_items(user_id, query, "photo", top_k_photo)

    # 통합 응답 생성
    result = generate_combined_answer_with_context(
        user_id, query, info_results, photo_results
    )

    # 전체 응답 저장 (assistant 역할로)
    serialized_result = json.dumps(result, ensure_ascii=False)
    save_chat_vector_to_pinecone(
        user_id, "assistant", serialized_result, int(time.time())
    )

    return result
