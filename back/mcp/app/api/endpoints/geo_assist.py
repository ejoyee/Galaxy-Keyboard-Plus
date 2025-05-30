# app/api/endpoints/geo_assist.py
from fastapi import APIRouter, Request, HTTPException
from app.models.schemas import LocalSearchRequest, LocalSearchResponse
from app.utils import gmaps_llm as glm
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
)
async def geo_assist(request: Request, body: LocalSearchRequest):
    loc = body.location.dict()
    lat, lon = loc["latitude"], loc["longitude"]
    query = body.query

    mcp = request.app.state.mcp_manager

    # 1) 현재 위치 좌표를 주소로 변환 (경로 요청인 경우에만)
    current_address = None
    if any(keyword in query.lower() for keyword in ["가는", "방법", "경로", "길", "어떻게"]):
        try:
            reverse_result = await _maps(mcp, "maps_reverse_geocode", {
                "latitude": lat,
                "longitude": lon
            })
            
            # reverse_geocode 결과에서 주소 추출
            if "result" in reverse_result and reverse_result["result"]:
                if isinstance(reverse_result["result"], dict):
                    current_address = reverse_result["result"].get("formatted_address", f"{lat},{lon}")
                elif isinstance(reverse_result["result"], list) and len(reverse_result["result"]) > 0:
                    current_address = reverse_result["result"][0].get("formatted_address", f"{lat},{lon}")
                else:
                    current_address = f"{lat},{lon}"
            else:
                current_address = f"{lat},{lon}"
            
            log.info(f"현재 위치 주소 변환: {lat},{lon} -> {current_address}")
        except Exception as e:
            log.warning(f"주소 변환 실패, 좌표 사용: {e}")
            current_address = f"{lat},{lon}"

    # 2) LLM에게 어떤 Maps 툴을 사용할지 결정 (변환된 주소 정보 포함)
    decision = await glm.choose_tool(
        query, 
        lat=lat, 
        lon=lon, 
        current_address=current_address
    )
    log.info("LLM decision: %s", decision)

    # 2-A) 툴 필요 없는 단순 답변
    if "tool" not in decision:
        html = f"<div style='padding:12px;font-size:16px'>{decision['text']}</div>"
        return LocalSearchResponse(answer=html)

    tool_name = decision["tool"]
    arguments = decision["arguments"]

    # 3) 파라미터 보정
    if tool_name == "maps_search_places":
        arguments.setdefault("location", {"latitude": lat, "longitude": lon})
        arguments.setdefault("radius", 1000)
        if "keyword" in arguments:
            arguments["query"] = arguments.pop("keyword")
        html_kind = "places"
    else:  # maps_directions
        # 변환된 주소가 있으면 주소를 사용, 없으면 좌표 사용
        if current_address:
            arguments.setdefault("origin", current_address)
        else:
            arguments.setdefault("origin", f"{lat},{lon}")
        arguments.setdefault("mode", "transit")
        html_kind = "route"

    # 4) MCP 호출
    raw = await _maps(mcp, tool_name, arguments)

    # 5) HTML 변환 (원본 query와 출발지 정보도 함께 전달)
    html = await glm.to_html(
        raw, 
        query, 
        kind=html_kind,
        origin_info={
            "address": current_address,
            "coordinates": f"{lat},{lon}"
        }
    )
    return HTMLResponse(content=html)