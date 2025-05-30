from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from app.utils.llm import call_llm, summarize_with_llm, call_llm_for_airbnb
import logging
import time

router = APIRouter()
logger = logging.getLogger(__name__)


# 요청 바디 스키마 정의
class AirbnbSearchQuery(BaseModel):
    query: str


# 응답 스키마 정의
class AirbnbSearchResponse(BaseModel):
    answer: str


@router.post(
    "/airbnb-search",
    response_model=AirbnbSearchResponse,
    summary="Airbnb 숙소 검색 (자연어 기반)",
    description="자연어 쿼리를 받아 Airbnb MCP를 통해 숙소를 검색합니다.",
    response_description="요약된 숙소 설명",
    tags=["Airbnb"],
)
async def airbnb_search_endpoint(request: Request, body: AirbnbSearchQuery):
    start = time.perf_counter()
    query = body.query

    logger.info(f"[airbnb_search_endpoint] 요청 쿼리: {query}")

    mcp_manager = request.app.state.mcp_manager

    # LLM이 툴 파라미터 추론
    try:
        # tools_info = mcp_manager.get_all_tools()
        llm_result = await call_llm_for_airbnb(query)
        logger.info(f"[airbnb_search_endpoint] LLM 결과: {llm_result}")
    except Exception as e:
        logger.error(f"[airbnb_search_endpoint] LLM 호출 실패: {e}")
        raise HTTPException(status_code=500, detail="LLM 처리 실패")

    # MCP 호출
    if llm_result.get("type") == "rpc":
        try:
            result = await mcp_manager.call_tool(
                server_name=llm_result["srvId"],
                tool_name=llm_result["method"],
                arguments=llm_result["params"],
            )
        except Exception as e:
            logger.error(f"[airbnb_search_endpoint] MCP 호출 실패: {e}")
            raise HTTPException(status_code=500, detail="Airbnb MCP 호출 실패")

        summarized = await summarize_with_llm(result, prompt=query)
        answer = summarized.get("results", [{}])[0].get("description", "")
    else:
        # LLM 자체 응답
        answer = llm_result.get("content", "")

    elapsed = time.perf_counter() - start
    logger.info(f"[airbnb_search_endpoint] 완료 (소요 시간: {elapsed:.3f}초)")

    return AirbnbSearchResponse(answer=answer)
