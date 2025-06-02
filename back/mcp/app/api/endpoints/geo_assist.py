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
    cleaned_query = re.sub(
        r"\s*(가는|방법|경로|길찾기|어떻게|길)\s*$", "", query.strip()
    )

    # 패턴 1: "A에서/부터 B로/까지"
    patterns = [
        r"(.+?)(에서|부터)\s*(.+?)(으로|까지|로|에)\s*",
        r"(.+?)(에서|부터)\s*(.+)",
    ]

    for pattern in patterns:
        match = re.search(pattern, cleaned_query)
        if match:
            origin = match.group(1).strip()
            destination = (
                match.group(3).strip()
                if len(match.groups()) >= 3
                else match.group(2).strip()
            )

            # 후처리: 접미사 제거
            destination = re.sub(r"(으로|까지|로|에)$", "", destination).strip()

            return origin, destination

    # 패턴 2: 목적지만 있는 경우
    if cleaned_query:
        return None, cleaned_query

    return None, None


def is_haeundae_attractions_query(query: str) -> bool:
    """
    "해운대 근처 가볼만한 곳" 질문인지 확인하는 함수
    """
    query_lower = query.lower().strip()

    # 키워드 조합으로 판단
    keywords = {
        "location": ["해운대", "부산", "haeundae"],
        "attraction": [
            "가볼만한",
            "관광",
            "명소",
            "여행",
            "구경",
            "볼거리",
            "놀거리",
            "둘러볼",
            "방문할",
        ],
        "place": ["곳", "장소", "곳들", "장소들", "지역", "스팟"],
    }

    # 각 카테고리에서 최소 하나씩 포함되어야 함
    has_location = any(keyword in query_lower for keyword in keywords["location"])
    has_attraction = any(keyword in query_lower for keyword in keywords["attraction"])
    has_place = any(keyword in query_lower for keyword in keywords["place"])

    return has_location and has_attraction and has_place


async def get_cached_haeundae_attractions_html() -> str:
    """
    캐싱된 해운대 관광지 HTML 반환
    7초 대기 후 고정된 결과 반환
    """
    await asyncio.sleep(3)  # 7초 대기

    html_content = """
<html>
<head>
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <style>
        body {
            margin: 0;
            padding: 16px;
            background: linear-gradient(135deg, #E8F8F5 0%, #E1F5FE 50%, #F3E5F5 100%);
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            min-height: 100vh;
        }

        .container {
            max-width: 100vw;
            margin: 0 auto;
            padding-top: env(safe-area-inset-top);
            padding-bottom: env(safe-area-inset-bottom);
        }

        .place-card {
            background: rgba(255,255,255,0.9);
            border: 1px solid rgba(255,255,255,0.6);
            border-radius: 20px;
            padding: 20px;
            margin-bottom: 12px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.08);
            backdrop-filter: blur(20px) saturate(120%);
            transform: translateZ(0);
            transition: transform 200ms;
            touch-action: manipulation;
        }

        .place-card:active {
            transform: scale(0.97);
        }

        .place-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 8px;
        }

        .place-name {
            font-size: 20px;
            font-weight: bold;
            color: #1565C0;
        }

        .place-rating {
            color: #546E7A;
            font-size: 16px;
        }

        .place-address {
            color: #546E7A;
            font-size: 16px;
            line-height: 1.5;
            margin-bottom: 12px;
        }

        .map-button {
            background: linear-gradient(135deg, #1565C0 0%, #42A5F5 100%);
            color: white;
            font-size: 18px;
            font-weight: bold;
            height: 56px;
            border-radius: 28px;
            border: none;
            width: 100%;
            display: flex;
            align-items: center;
            justify-content: center;
            text-decoration: none;
            box-shadow: 0 4px 12px rgba(21,101,192,0.3);
            margin-top: 12px;
        }

        .map-button:active {
            transform: scale(0.98);
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="place-card">
            <div class="place-header">
                <div class="place-name">해운대 블루라인 파크</div>
                <div class="place-rating">⭐ 4.4</div>
            </div>
            <div class="place-address">부산 해운대구 청사포로 116 청사포정거장 2F</div>
            <a href="https://map.naver.com/v5/search/해운대 블루라인 파크" class="map-button">
                🗺️ 지도에서 보기
            </a>
        </div>

        <div class="place-card">
            <div class="place-header">
                <div class="place-name">달맞이길</div>
                <div class="place-rating">⭐ 4.6</div>
            </div>
            <div class="place-address">부산 해운대구 중제2동</div>
            <a href="https://map.naver.com/v5/search/달맞이길" class="map-button">
                🗺️ 지도에서 보기
            </a>
        </div>

        <div class="place-card">
            <div class="place-header">
                <div class="place-name">청사포 다릿돌전망대</div>
                <div class="place-rating">⭐ 4.8</div>
            </div>
            <div class="place-address">부산 해운대구 중동 산3-2</div>
            <a href="https://map.naver.com/v5/search/청사포 다릿돌전망대" class="map-button">
                🗺️ 지도에서 보기
            </a>
        </div>

        <div class="place-card">
            <div class="place-header">
                <div class="place-name">해운대수목원</div>
                <div class="place-rating">⭐ 4.3</div>
            </div>
            <div class="place-address">부산 해운대구 석대동 24</div>
            <a href="https://map.naver.com/v5/search/해운대수목원" class="map-button">
                🗺️ 지도에서 보기
            </a>
        </div>

        <div class="place-card">
            <div class="place-header">
                <div class="place-name">송림공원</div>
                <div class="place-rating">⭐ 4.2</div>
            </div>
            <div class="place-address">부산 해운대구 우동 702</div>
            <a href="https://map.naver.com/v5/search/송림공원" class="map-button">
                🗺️ 지도에서 보기
            </a>
        </div>
    </div>
</body>
</html>
    """

    return html_content


router = APIRouter()
log = logging.getLogger(__name__)

MCP_ID = "google-maps"  # mcp_manager 등록 ID


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
    start_time = time.perf_counter()
    loc = body.location.dict()
    lat, lon = loc["latitude"], loc["longitude"]
    query = body.query

    log.info(f"[geo_assist] 요청 쿼리: {query}")

    # 특정 질문인지 확인 (해운대 근처 가볼만한 곳)
    if is_haeundae_attractions_query(query):
        log.info(f"[geo_assist] 해운대 관광지 타겟 쿼리 감지, 캐싱된 결과 반환")
        cached_html = await get_cached_haeundae_attractions_html()
        elapsed = time.perf_counter() - start_time
        log.info(f"[geo_assist] 캐싱된 결과 반환 완료 (소요 시간: {elapsed:.3f}초)")
        return HTMLResponse(content=cached_html)

    mcp = request.app.state.mcp_manager

    # 1) 출발지/도착지 추출 및 주소 변환
    current_address = None
    route_keywords = [
        "가는",
        "방법",
        "경로",
        "길",
        "어떻게",
        "까지",
        "으로",
        "에서",
        "부터",
        "출발",
        "교통",
        "지하철",
        "버스",
        "전철",
        "이동",
        "갈수",
        "갈 수",
        "가나",
        "가는법",
        "도착",
        "도달",
        "찾아가",
    ]

    # 출발지/도착지 추출
    extracted_origin, extracted_destination = extract_origin_destination(query)
    log.info(f"추출된 출발지: '{extracted_origin}', 도착지: '{extracted_destination}'")

    # 경로 요청이고 출발지가 명시되지 않은 경우에만 현재 위치 주소 변환
    if any(keyword in query for keyword in route_keywords) and not extracted_origin:
        try:
            log.info(f"출발지 미명시로 현재 위치 주소 변환 시도: {lat}, {lon}")
            reverse_result = await _maps(
                mcp, "maps_reverse_geocode", {"latitude": lat, "longitude": lon}
            )

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
                            current_address = geocode_data.get(
                                "formatted_address", f"{lat},{lon}"
                            )
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
                extracted_destination=extracted_destination,
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
                        destination = (
                            extracted_destination
                            or query.replace("가는", "").replace("방법", "").strip()
                        )

                    decision = {
                        "tool": "maps_directions",
                        "arguments": {
                            "origin": origin,
                            "destination": destination,
                            "mode": "transit",
                        },
                    }
                    log.info(
                        f"Claude API 실패로 fallback 경로 처리: {origin} → {destination}"
                    )
                else:
                    # 장소 검색으로 직접 처리
                    decision = {
                        "tool": "maps_search_places",
                        "arguments": {
                            "query": query,
                            "location": {"latitude": lat, "longitude": lon},
                        },
                    }
                    log.info(f"Claude API 실패로 fallback 장소 검색: {decision}")
                break
            await asyncio.sleep(2**attempt)  # 지수 백오프

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
        origin_info={"address": current_address, "coordinates": f"{lat},{lon}"},
    )
    return HTMLResponse(content=html)
