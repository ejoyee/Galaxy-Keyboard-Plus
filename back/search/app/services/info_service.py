import asyncio
import logging
import time
import json
import re
import requests
from typing import List, Dict, Optional
from app.utils.ai_utils import expand_info_query
from app.utils.semantic_search import search_similar_items_enhanced_optimized
from app.utils.context_helpers import (
    check_if_requires_context,
    get_chat_context,
    generate_contextualized_info_answer,
)
from app.config.settings import MAX_CONTEXT_ITEMS
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)
executor = ThreadPoolExecutor(max_workers=10)


async def process_info_search(user_id: str, query: str, timings: Dict) -> Dict:
    """정보 검색 처리 - MCP 서버 직접 호출"""
    logger.info(f"🔍 MCP 서버 직접 호출 시작 - query: {query}")

    # MCP 서버에 바로 요청
    mcp_start = time.time()
    answer = await call_mcp_server_direct(query)
    timings["mcp_request"] = time.time() - mcp_start

    logger.info(f"✅ MCP 서버 응답 완료 ({timings['mcp_request']:.3f}초)")

    # 결과 구성 (이미지 관련 필드 제거)
    return {
        "type": "info_search",
        "query": query,
        "answer": answer,
        "context_count": 0,  # 벡터 검색 안 함
        "chat_context_used": False,  # 대화 맥락 사용 안 함
        "photo_ids": [],  # 이미지 ID 없음
        "_timings": timings,
        "_debug": {
            "direct_mcp_call": True,
            "vector_search_skipped": True,
        },
    }


async def call_mcp_server_direct(query: str) -> str:
    """MCP 서버에 직접 요청하여 답변 생성"""

    def sync_call_mcp():
        # 원본 쿼리를 그대로 MCP 서버에 전달
        final_query = f"""
사용자의 질문: "{query}"

질문에 대한 정확한 정보를 찾지 못했다면, 웹검색을 통해 최대한 관련된 내용을 제공해보세요. 
정보가 부족하더라도 사용자의 질문에 유용한 답변을 제공하되, 추측임을 명시하고 정확한 정보를 제공하는 방식으로 작성해주세요.
사용자가 참고할 수 있는 URL을 3개정도 마지막에 포함해주세요. URL 제목은 그 링크에 대한 설명으로 해주세요.

답변:
"""

        # MCP API로 요청
        try:
            headers = {
                "accept": "application/json",
                "Content-Type": "application/json",
            }

            payload = {"query": final_query}

            logger.info(f"🚀 MCP API 직접 요청 시작: 쿼리 길이 {len(final_query)} 자")
            mcp_start_time = time.time()

            response = requests.post(
                "http://mcp-api:8050/api/search/",
                # "http://k12e201.p.ssafy.io:8050/api/search/",
                headers=headers,
                json=payload,
                timeout=30,  # 타임아웃 설정
            )

            mcp_response_time = time.time() - mcp_start_time
            logger.info(f"✅ MCP API 직접 응답 수신: {mcp_response_time:.3f}초")

            if response.status_code == 200:
                result = response.json()
                answer = result.get(
                    "answer", "죄송합니다. 답변을 생성하는 데 문제가 발생했습니다."
                )
                logger.info(f"📝 MCP 서버 답변 길이: {len(answer)} 자")
            else:
                error_time = time.time() - mcp_start_time
                logger.error(
                    f"❌ MCP API 응답 오류 ({error_time:.3f}초): 상태 코드 {response.status_code}, 응답: {response.text}"
                )
                answer = "죄송합니다. 답변을 생성하는 데 문제가 발생했습니다."
        except requests.exceptions.Timeout:
            error_time = time.time() - mcp_start_time
            logger.error(f"⏱️ MCP API 타임아웃 발생 ({error_time:.3f}초)")
            answer = "죄송합니다. 서버 응답 시간이 너무 오래 걸립니다."
        except requests.exceptions.ConnectionError:
            error_time = time.time() - mcp_start_time
            logger.error(
                f"🔌 MCP API 연결 오류 ({error_time:.3f}초): 서버에 연결할 수 없습니다."
            )
            answer = "죄송합니다. MCP 서버에 연결할 수 없습니다."
        except Exception as e:
            error_time = time.time() - mcp_start_time
            logger.error(
                f"❌ MCP API 요청 오류 ({error_time:.3f}초): {str(e)}", exc_info=True
            )
            answer = "죄송합니다. 서버 통신 중 오류가 발생했습니다."

        return answer

    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(executor, sync_call_mcp)


async def perform_vector_search(
    user_id: str, expanded_queries: List[str], original_query: str
) -> List[Dict]:
    """벡터 검색 수행"""
    context_info = []
    loop = asyncio.get_event_loop()

    try:
        # 1. 확장된 쿼리로 검색
        result1 = await loop.run_in_executor(
            executor,
            search_similar_items_enhanced_optimized,
            user_id,
            expanded_queries,
            "information",
            20,
        )
        context_info.extend(result1)
        logger.info(f"✅ 확장된 쿼리 결과: {len(result1)}개")

        # 2. 원본 쿼리로도 검색
        if len(context_info) < 5:
            result2 = await loop.run_in_executor(
                executor,
                search_similar_items_enhanced_optimized,
                user_id,
                [original_query],
                "information",
                10,
            )
            context_info.extend(result2)
            logger.info(f"✅ 원본 쿼리 결과: {len(result2)}개")

        # 중복 제거
        seen_texts = set()
        unique_results = []
        for item in context_info:
            text = item.get("text", "")
            if text and text not in seen_texts:
                seen_texts.add(text)
                unique_results.append(item)

        return unique_results[:MAX_CONTEXT_ITEMS]

    except Exception as e:
        logger.error(f"❌ 벡터 검색 실패: {str(e)}", exc_info=True)
        return []


async def generate_enhanced_info_answer(
    user_id: str, query: str, context_info: List[Dict]
) -> tuple[str, List[int]]:
    """개선된 정보 기반 답변 생성 - MCP API를 사용하여 답변 생성"""

    def sync_generate_enhanced_answer():
        # context 정보를 더 체계적으로 정리
        context_texts = []
        for i, item in enumerate(context_info[:5]):  # 상위 5개만 사용
            text = item.get("text", "").strip()
            if text:
                context_texts.append(f"{i+1}. {text}")

        context_text = "\n".join(context_texts)

        # 최종 쿼리 구성
        if context_text:
            final_query = f"""
사용자의 질문에 대해 아래 제공된 정보를 활용하여 답변하세요.
정보가 부족하더라도 최대한 관련된 내용을 추출하여 자연스러운 답변을 구성하세요.

[제공된 정보]
{context_text}

[사용자 질문]
{query}

답변 작성 규칙:
1. 제공된 정보를 기반으로 정확하게 답변
2. 친근하고 자연스러운 대화체 사용
3. 정보가 부족한 경우에도 질문에 맞는 답변 제공
4. 알려진 정보만으로 답변하되, 의미있는 정보가 전혀 없는 경우 적절히 안내
5. "제공된 정보에는 없지만"이라는 표현은 사용하지 말 것

질문에 대한 정확한 정보를 찾지 못했다면, 웹검색을 통해 최대한 관련된 내용을 제공해보세요. 
정보가 부족하더라도 사용자의 질문에 유용한 답변을 제공하되, 추측임을 명시하고 정확한 정보를 제공하는 방식으로 작성해주세요.
사용자가 참고할 수 있는 URL을 3개정도 마지막에 포함해주세요. URL 제목은 그 링크에 대한 설명으로 해주세요.
답변:
"""
        else:
            # 컨텍스트가 없는 경우
            final_query = f"""
사용자의 질문: "{query}"

질문에 대한 정확한 정보를 찾지 못했다면, 웹검색을 통해 최대한 관련된 내용을 제공해보세요. 
정보가 부족하더라도 사용자의 질문에 유용한 답변을 제공하되, 추측임을 명시하고 정확한 정보를 제공하는 방식으로 작성해주세요.

답변:
"""

        # MCP API로 요청
        try:
            headers = {
                "accept": "application/json",
                "Content-Type": "application/json",
            }

            payload = {"query": final_query}

            logger.info(f"🚀 MCP API 요청 시작: 쿼리 길이 {len(final_query)} 자")
            mcp_start_time = time.time()

            response = requests.post(
                # "http://mcp-api:8050/api/search/",
                "http://k12e201.p.ssafy.io:8050/api/search/",
                headers=headers,
                json=payload,
                timeout=30,  # 타임아웃 설정
            )

            mcp_response_time = time.time() - mcp_start_time
            logger.info(f"✅ MCP API 응답 수신: {mcp_response_time:.3f}초")

            if response.status_code == 200:
                mcp_parse_start = time.time()
                result = response.json()
                answer = result.get(
                    "answer", "죄송합니다. 답변을 생성하는 데 문제가 발생했습니다."
                )

                mcp_parse_time = time.time() - mcp_parse_start
                total_mcp_time = time.time() - mcp_start_time

                logger.info(
                    f"""
📊 MCP API 성능 요약:
- 요청-응답 시간: {mcp_response_time:.3f}초
- 응답 파싱 시간: {mcp_parse_time:.3f}초
- 전체 처리 시간: {total_mcp_time:.3f}초
- 응답 길이: {len(answer)} 자
                """
                )
            else:
                error_time = time.time() - mcp_start_time
                logger.error(
                    f"❌ MCP API 응답 오류 ({error_time:.3f}초): 상태 코드 {response.status_code}, 응답: {response.text}"
                )
                answer = "죄송합니다. 답변을 생성하는 데 문제가 발생했습니다."
        except requests.exceptions.Timeout:
            error_time = time.time() - mcp_start_time
            logger.error(f"⏱️ MCP API 타임아웃 발생 ({error_time:.3f}초)")
            answer = "죄송합니다. 서버 응답 시간이 너무 오래 걸립니다."
        except requests.exceptions.ConnectionError:
            error_time = time.time() - mcp_start_time
            logger.error(
                f"🔌 MCP API 연결 오류 ({error_time:.3f}초): 서버에 연결할 수 없습니다."
            )
            answer = "죄송합니다. MCP 서버에 연결할 수 없습니다."
        except Exception as e:
            error_time = time.time() - mcp_start_time
            logger.error(
                f"❌ MCP API 요청 오류 ({error_time:.3f}초): {str(e)}", exc_info=True
            )
            answer = "죄송합니다. 서버 통신 중 오류가 발생했습니다."

        # 사용된 컨텍스트 인덱스 추출
        used_indices = []
        if context_text:  # 컨텍스트가 있었을 때만 추출
            # 답변 끝부분에서 번호 목록 추출
            indices_pattern = r"\b([0-9]+(?:,\s*[0-9]+)*)\b"
            indices_matches = re.findall(indices_pattern, answer.split("\n")[-1])

            if indices_matches:
                # 마지막 변에서 받은 것이 리스트의 형태로 도출되면 그걸 사용
                last_match = indices_matches[-1]
                for idx_str in last_match.split(","):
                    try:
                        idx = int(idx_str.strip()) - 1  # 1-based -> 0-based
                        if 0 <= idx < len(context_info):
                            used_indices.append(idx)
                    except ValueError:
                        continue

            # 수처리된 마지막 행을 제거 (외부에서 보이지 않게)
            if used_indices and "\n" in answer:
                lines = answer.split("\n")
                if any(
                    all(c in "0123456789, " for c in line.strip())
                    for line in lines[-2:]
                ):
                    answer = "\n".join(lines[:-1]).strip()

        return answer, used_indices

    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(executor, sync_generate_enhanced_answer)


def extract_id_from_item(item: Dict) -> Optional[str]:
    """한 개의 검색 결과 항목에서 ID 추출"""
    # ID가 이미 있는 경우
    if "id" in item and item["id"] not in ["unknown", ""]:
        return item["id"]

    text = item.get("text", "")
    if not text:
        return None

    # 1. 단순 숫자로 시작하는 영수증 번호 패턴
    receipt_id_match = re.match(r"^(\d{5,10})", text.strip())
    if receipt_id_match:
        return receipt_id_match.group(1)

    # 2. "숫자: " 형태의 ID
    prefix_id_match = re.match(r"^(\d+):\s", text.strip())
    if prefix_id_match:
        return prefix_id_match.group(1)

    # 3. 첫 줄이 숫자로만 이루어진 경우
    first_line = text.strip().split("\n")[0].strip() if "\n" in text else ""
    if first_line and first_line.isdigit() and len(first_line) > 4:
        return first_line

    return None
