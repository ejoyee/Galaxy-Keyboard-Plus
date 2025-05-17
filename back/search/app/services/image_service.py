import asyncio
import logging
import time
import json
from typing import List, Dict
from app.utils.ai_utils import determine_image_query_intent, extract_photo_keywords
from app.utils.db_utils import search_photos_by_keywords
from app.utils.async_utils import save_query_async, save_result_async
from app.config.settings import MAX_DISPLAY_RESULTS

logger = logging.getLogger(__name__)


async def process_photo_search(user_id: str, query: str, timings: Dict) -> Dict:
    """사진 검색 처리 - 최소 3개 이상의 키워드 매칭 필요"""
    # 키워드 추출
    keyword_start = time.time()
    keywords = await extract_photo_keywords(query)
    timings["keyword_extraction"] = time.time() - keyword_start
    logger.info(
        f"🔍 추출된 키워드 ({len(keywords)}개): {keywords[:10]} ({timings['keyword_extraction']:.3f}초)"
    )

    # DB에서 사진 검색
    db_search_start = time.time()
    photo_results = await search_photos_by_keywords(user_id, keywords)
    timings["db_search"] = time.time() - db_search_start

    # 결과 필터링 - 최소 3개 이상의 키워드 매칭 및 높은 점수만 포함
    min_keyword_match = 3  # 최소 키워드 매칭 개수
    min_score = 3.0  # 최소 필요 점수

    # 기존 검색 결과 수 저장
    total_results = len(photo_results)

    # 필터링 적용
    filtered_results = [
        photo
        for photo in photo_results
        if photo["match_count"] >= min_keyword_match and photo["score"] >= min_score
    ]

    # 기본 오름차순 정렬 (어차피 SQL에서 정렬되어 오지만 확인용)
    filtered_results.sort(key=lambda x: (-x["score"], -x["match_count"]))

    # 필터링 된 결과가 없을 경우, 점수가 가장 높은 상위 5개 포함 (사용자 경험 개선)
    if not filtered_results and photo_results:
        filtered_results = sorted(
            photo_results, key=lambda x: (-x["score"], -x["match_count"])
        )[:5]
        logger.info(
            f"🔍 필터링 결과 없어 상위 5개 추가: {'-'.join([p['access_id'] for p in filtered_results])}"
        )

    # photo_ids만 추출
    photo_ids = [photo["access_id"] for photo in filtered_results]

    logger.info(
        f"📷 검색된 사진: 총 {total_results}개 중 {len(photo_ids)}개 필터링 ({timings['db_search']:.3f}초)"
    )

    # 결과 구성 - photo_search에서는 answer를 빈 문자열로 설정
    return {
        "type": "photo_search",
        "query": query,
        "keywords": keywords,
        "photo_ids": photo_ids,
        "photo_details": filtered_results[:MAX_DISPLAY_RESULTS],  # 상위 N개 상세 정보
        "answer": "",  # photo_search에서는 반드시 빈 문자열로 설정
        "count": len(photo_ids),
        "total_results": total_results,  # 총 검색 결과 수 추가
        "_filter_criteria": {  # 필터링 기준 디버그용
            "min_keywords": min_keyword_match,
            "min_score": min_score,
        },
        "_timings": timings,
    }
