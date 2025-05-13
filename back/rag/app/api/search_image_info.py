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
import asyncio
from concurrent.futures import ThreadPoolExecutor

router = APIRouter()


@router.post("/search/")
async def search(
    user_id: str = Form(...),
    query: str = Form(...),
    top_k_photo: Optional[int] = Form(10),
    top_k_info: Optional[int] = Form(10),
    use_context: Optional[bool] = Form(True),
):
    timestamp = int(time.time())

    # 현재 이벤트 루프 가져오기
    loop = asyncio.get_event_loop()
    executor = ThreadPoolExecutor(max_workers=10)

    # 비동기로 병렬 처리 가능한 작업들
    tasks = []

    # 1. 사용자 쿼리 저장 (Future 객체 직접 사용)
    save_query_future = loop.run_in_executor(
        executor,
        save_chat_vector_to_pinecone,
        user_id,
        "user",
        query,
        timestamp,
    )
    tasks.append(save_query_future)

    # 2. 쿼리 타입 확인 (Future)
    query_type_future = loop.run_in_executor(executor, determine_query_type, query)

    # 3. 쿼리 개선
    enhanced_query = query
    if use_context:
        context_keywords = ["이전에", "아까", "방금", "그때", "다시", "그거", "그것"]
        needs_context = any(keyword in query for keyword in context_keywords)

        if needs_context:
            enhance_future = loop.run_in_executor(
                executor, enhance_query_with_personal_context, user_id, query
            )
            enhanced_query = await enhance_future

    # 4. 벡터 검색 병렬 처리
    info_search_future = loop.run_in_executor(
        executor, search_similar_items, user_id, enhanced_query, "info", top_k_info
    )

    photo_search_future = loop.run_in_executor(
        executor,
        search_similar_items,
        user_id,
        enhanced_query,
        "photo",
        top_k_photo,
    )

    # 검색 결과 대기
    raw_info_results, raw_photo_results = await asyncio.gather(
        info_search_future, photo_search_future
    )

    # 5. LLM 필터링 병렬 처리
    info_filter_future = loop.run_in_executor(
        executor,
        filter_relevant_items_with_llm,
        enhanced_query,
        raw_info_results,
        "정보",
    )

    photo_filter_future = loop.run_in_executor(
        executor,
        filter_relevant_items_with_llm,
        enhanced_query,
        raw_photo_results,
        "사진",
    )

    # 필터링 결과 대기
    info_results, photo_results = await asyncio.gather(
        info_filter_future, photo_filter_future
    )

    # 6. 최종 답변 생성
    result = await loop.run_in_executor(
        executor,
        generate_combined_answer_with_context,
        user_id,
        enhanced_query,
        info_results,
        photo_results,
    )

    # 7. 응답 저장 (비차단)
    serialized_result = json.dumps(result, ensure_ascii=False)
    save_response_future = loop.run_in_executor(
        executor,
        save_chat_vector_to_pinecone,
        user_id,
        "assistant",
        serialized_result,
        int(time.time()),
    )
    tasks.append(save_response_future)

    # 백그라운드 작업 완료 대기 (선택사항)
    if tasks:
        await asyncio.gather(*tasks, return_exceptions=True)

    # executor 정리
    executor.shutdown(wait=False)

    return result
