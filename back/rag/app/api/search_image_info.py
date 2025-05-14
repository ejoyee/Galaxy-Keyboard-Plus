from fastapi import APIRouter, Form
from typing import Optional
from app.utils.semantic_search import (
    enhance_query_with_personal_context_v2,
    determine_query_intent,
    search_similar_items_enhanced,
    filter_relevant_items_with_context,
    generate_answer_by_intent,
)
from app.utils.chat_vector_store import save_chat_vector_to_pinecone
import json, time
import asyncio
from concurrent.futures import ThreadPoolExecutor
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

# ThreadPoolExecutor 워커 수 증가
executor = ThreadPoolExecutor(max_workers=20)  # 기존 5에서 20으로 증가


@router.post("/search/")
async def search(
    user_id: str = Form(...),
    query: str = Form(...),
    top_k_photo: Optional[int] = Form(7),
    top_k_info: Optional[int] = Form(7),
):
    timestamp = int(time.time())
    loop = asyncio.get_event_loop()

    try:
        # 기존 코드 그대로 유지
        save_task = loop.run_in_executor(
            executor, save_chat_vector_to_pinecone, user_id, "user", query, timestamp
        )

        expanded_queries = await loop.run_in_executor(
            executor, enhance_query_with_personal_context_v2, user_id, query
        )

        logger.info(f"🔍 의미 기반 확장 쿼리 (Top 3): {expanded_queries[:3]}")

        query_intent = determine_query_intent(query)

        info_search_task = loop.run_in_executor(
            executor,
            search_similar_items_enhanced,
            user_id,
            expanded_queries,
            "info",
            top_k_info,
        )

        photo_search_task = loop.run_in_executor(
            executor,
            search_similar_items_enhanced,
            user_id,
            expanded_queries,
            "photo",
            top_k_photo,
        )

        raw_info_results, raw_photo_results = await asyncio.gather(
            info_search_task, photo_search_task
        )

        info_filter_task = loop.run_in_executor(
            executor,
            filter_relevant_items_with_context,
            query,
            "",
            raw_info_results,
            "정보",
        )

        photo_filter_task = loop.run_in_executor(
            executor,
            filter_relevant_items_with_context,
            query,
            "",
            raw_photo_results,
            "사진",
        )

        info_results, photo_results = await asyncio.gather(
            info_filter_task, photo_filter_task
        )

        result = await loop.run_in_executor(
            executor,
            generate_answer_by_intent,
            user_id,
            query,
            info_results,
            photo_results,
            query_intent,
        )

        serialized_result = json.dumps(result, ensure_ascii=False)
        await loop.run_in_executor(
            executor,
            save_chat_vector_to_pinecone,
            user_id,
            "assistant",
            serialized_result,
            int(time.time()),
        )

        return result

    finally:
        # executor.shutdown(wait=False) 제거 - 재사용해야 함
        pass


# 애플리케이션 종료 시에만 정리
@router.on_event("shutdown")
async def shutdown_event():
    executor.shutdown(wait=True)
