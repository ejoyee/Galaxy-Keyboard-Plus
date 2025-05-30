# app/api/endpoints/geo_assist.py
from fastapi import APIRouter, Request, HTTPException
from app.models.schemas import LocalSearchRequest, LocalSearchResponse
from app.utils import gmaps_llm as glm
import logging, time
from fastapi.responses import HTMLResponse
import re
import asyncio

def extract_origin_destination(query: str):
    """쿼리에서 출발지와 도착지를 추출"""
    # 정리: 불필요한 단어 제거
    cleaned_query = re.sub(r'\s*(가는|방법|경로|길찾기|어떻게|길)\s*$', '', query.strip())
    
    # 패턴 1: "A에서/부터 B로/까지"
    patterns = [
        r'(.+?)(에서|부터)\s*(.+?)(으로|까지|로|에)\s*',
        r'(.+?)(에서|부터)\s*(.+)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, cleaned_query)
        if match:
            origin = match.group(1).strip()
            destination = match.group(3).strip() if len(match.groups()) >= 3 else match.group(2).strip()
            
            # 후처리: 접미사 제거
            destination = re.sub(r'(으로|까지|로|에)$', '', destination).strip()
            
            return origin, destination
    
    # 패턴 2: 목적지만 있는 경우
    if cleaned_query:
        return None, cleaned_query
    
    return None, None


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

    # 1) 출발지/도착지 추출 및 주소 변환
    current_address = None
    route_keywords = [
        "가는", "방법", "경로", "길", "어떻게",
        "까지", "으로", "에서", "부터", "출발", 
        "교통", "지하철", "버스", "전철",
        "이동", "갈수", "갈 수", "가나", "가는법",
        "도착", "도달", "찾아가"
    ]

    # 출발지/도착지 추출
    extracted_origin, extracted_destination = extract_origin_destination(query)
    log.info(f"추출된 출발지: '{extracted_origin}', 도착지: '{extracted_destination}'")


    # 경로 요청이고 출발지가 명시되지 않은 경우에만 현재 위치 주소 변환
    if any(keyword in query for keyword in route_keywords) and not extracted_origin:
        try:
            log.info(f"출발지 미명시로 현재 위치 주소 변환 시도: {lat}, {lon}")
            reverse_result = await _maps(mcp, "maps_reverse_geocode", {
                "latitude": lat,
                "longitude": lon
            })
            
            log.info(f"Reverse geocode 응답: {reverse_result}")
            
            # MCP 응답 구조에 맞춘 파싱
            if "result" in reverse_result and reverse_result["result"]:
                result = reverse_result["result"]
                
                if "content" in result and len(result["content"]) > 0:
                    try:
                        text_content = result["content"][0].get("text", "")
                        if text_content:
                            import json
                            geocode_data = json.loads(text_content)
                            current_address = geocode_data.get("formatted_address", f"{lat},{lon}")
                            log.info(f"현재 위치 주소 파싱 성공: {current_address}")
                        else:
                            current_address = f"{lat},{lon}"
                    except (json.JSONDecodeError, KeyError, IndexError) as e:
                        log.error(f"주소 JSON 파싱 실패: {e}")
                        current_address = f"{lat},{lon}"
                else:
                    current_address = f"{lat},{lon}"
            else:
                current_address = f"{lat},{lon}"
                
        except Exception as e:
            log.error(f"주소 변환 실패: {e}")
            current_address = f"{lat},{lon}"
    else:
        log.info("출발지가 명시되어 현재 위치 주소 변환 생략")



    # 2) LLM에게 어떤 Maps 툴을 사용할지 결정 (재시도 로직 포함)
    max_retries = 3
    decision = None

    for attempt in range(max_retries):
        try:
            decision = await glm.choose_tool(
                query, 
                lat=lat, 
                lon=lon, 
                current_address=current_address,
                extracted_origin=extracted_origin,
                extracted_destination=extracted_destination
            )
            break  # 성공시 루프 탈출
        except Exception as e:
            log.warning(f"LLM 호출 시도 {attempt + 1} 실패: {e}")
            if attempt == max_retries - 1:
                # Claude API가 계속 실패하면 직접 판단해서 처리
                if any(keyword in query for keyword in route_keywords):
                    # 경로 요청으로 직접 처리
                    if extracted_origin and extracted_destination:
                        # 출발지가 명시된 경우
                        origin = extracted_origin
                        destination = extracted_destination
                    else:
                        # 출발지 미명시된 경우 (현재 위치 사용)
                        origin = current_address or f"{lat},{lon}"
                        destination = extracted_destination or query.replace("가는", "").replace("방법", "").strip()
                    
                    decision = {
                        "tool": "maps_directions",
                        "arguments": {
                            "origin": origin,
                            "destination": destination,
                            "mode": "transit"
                        }
                    }
                    log.info(f"Claude API 실패로 fallback 경로 처리: {origin} → {destination}")
                else:
                    # 장소 검색으로 직접 처리
                    decision = {
                        "tool": "maps_search_places", 
                        "arguments": {
                            "query": query,
                            "location": {"latitude": lat, "longitude": lon}
                        }
                    }
                    log.info(f"Claude API 실패로 fallback 장소 검색: {decision}")
                break
            await asyncio.sleep(2 ** attempt)  # 지수 백오프

    if not decision:
        # 최악의 경우 에러 응답
        html = f"<div style='padding:20px;font-size:16px;color:#212529;background:#F8F9FA;'>죄송합니다. 현재 서비스가 일시적으로 과부하 상태입니다. 잠시 후 다시 시도해주세요.</div>"
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
        # 출발지가 추출된 경우 사용, 아니면 현재 위치 사용
        if extracted_origin:
            arguments.setdefault("origin", extracted_origin)
        elif current_address:
            arguments.setdefault("origin", current_address)
        else:
            arguments.setdefault("origin", f"{lat},{lon}")
        
        # 도착지 설정
        if extracted_destination:
            arguments.setdefault("destination", extracted_destination)
        
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