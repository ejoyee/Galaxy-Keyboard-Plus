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
    import logging

    logger = logging.getLogger(__name__)

    start_time = time.time()
    timestamp = int(time.time())

    # 각 단계 시간 측정
    step_times = {}

    # 현재 이벤트 루프 가져오기
    loop = asyncio.get_event_loop()
    executor = ThreadPoolExecutor(max_workers=10)

    # 1. 사용자 쿼리 저장
    save_start = time.time()
    save_query_future = loop.run_in_executor(
        executor,
        save_chat_vector_to_pinecone,
        user_id,
        "user",
        query,
        timestamp,
    )

    # 2. 쿼리 개선 (조건부)
    enhance_start = time.time()
    enhanced_query = query
    if use_context:
        context_keywords = ["이전에", "아까", "방금", "그때", "다시", "그거", "그것"]
        needs_context = any(keyword in query for keyword in context_keywords)

        if needs_context:
            enhance_future = loop.run_in_executor(
                executor, enhance_query_with_personal_context, user_id, query
            )
            enhanced_query = await enhance_future
    step_times["enhance"] = time.time() - enhance_start

    # 3. 벡터 검색 병렬 처리
    search_start = time.time()
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

    raw_info_results, raw_photo_results = await asyncio.gather(
        info_search_future, photo_search_future
    )
    step_times["vector_search"] = time.time() - search_start

    # 4. LLM 필터링 병렬 처리
    filter_start = time.time()
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

    info_results, photo_results = await asyncio.gather(
        info_filter_future, photo_filter_future
    )
    step_times["llm_filter"] = time.time() - filter_start

    # 5. 최종 답변 생성
    answer_start = time.time()
    result = await loop.run_in_executor(
        executor,
        generate_combined_answer_with_context,
        user_id,
        enhanced_query,
        info_results,
        photo_results,
    )
    step_times["generate_answer"] = time.time() - answer_start

    # 6. 응답 저장 (비차단)
    serialized_result = json.dumps(result, ensure_ascii=False)
    save_response_future = loop.run_in_executor(
        executor,
        save_chat_vector_to_pinecone,
        user_id,
        "assistant",
        serialized_result,
        int(time.time()),
    )

    # 백그라운드 작업 대기
    await asyncio.gather(
        save_query_future, save_response_future, return_exceptions=True
    )

    # 전체 시간 측정
    total_time = time.time() - start_time

    # 로그 출력
    logger.info(f"Total search time: {total_time:.2f}s")
    for step, duration in step_times.items():
        logger.info(f"{step}: {duration:.2f}s")

    executor.shutdown(wait=False)

    return result
