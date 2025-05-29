# app/api/endpoints/geo_assist.py
from fastapi import APIRouter, Request, HTTPException
from app.models.schemas import LocalSearchRequest, LocalSearchResponse
from app.utils import gmaps_llm as glm                      # ←★ 변경
import logging, time
from fastapi.responses import HTMLResponse

router = APIRouter()
log = logging.getLogger(__name__)

MCP_ID = "google-maps"   # mcp_manager 등록 ID


async def _maps(mcp, name: str, args: dict):
    """google-maps MCP 래퍼"""
    res = await mcp.call_tool(MCP_ID, name, args)
    if "error" in res:
        raise HTTPException(502, res["error"])
    return res


@router.post(
    "/",
    response_model=LocalSearchResponse,
    summary="위치 기반 지도 도우미",
    tags=["Geo Assist"],
)                       # ← 중복 데코레이터 제거
async def geo_assist(request: Request, body: LocalSearchRequest):
    loc = body.location.dict()
    lat, lon = loc["latitude"], loc["longitude"]
    query = body.query

    mcp = request.app.state.mcp_manager

    # 1) LLM에게 어떤 Maps 툴을 사용할지 결정
    decision = await glm.choose_tool(query, lat=lat, lon=lon)
    log.info("LLM decision: %s", decision)

    # 1-A) 툴 필요 없는 단순 답변
    if "tool" not in decision:
        html = f"<div style='padding:12px;font-size:16px'>{decision['text']}</div>"
        return LocalSearchResponse(answer=html)

    tool_name  = decision["tool"]
    arguments  = decision["arguments"]

    # 2) 파라미터 보정
    if tool_name == "maps_search_places":
        arguments.setdefault("location", {"latitude": lat, "longitude": lon})
        arguments.setdefault("radius", 1000)
        if "keyword" in arguments:
            arguments["query"] = arguments.pop("keyword")
        html_kind = "places"
    else:  # maps_directions
        arguments.setdefault("origin", f"{lat},{lon}")
        html_kind = "route"

    # 3) MCP 호출
    raw = await _maps(mcp, tool_name, arguments)

    # 4) HTML 변환
    html = await glm.to_html(raw, query, kind=html_kind)
    return HTMLResponse(content=html)
