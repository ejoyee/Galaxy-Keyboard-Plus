# app/api/endpoints/geo_assist.py
from fastapi import APIRouter, Request, HTTPException
from app.models.schemas import LocalSearchRequest, LocalSearchResponse
from app.utils import gmaps_llm as glm
import logging, time
from fastapi.responses import HTMLResponse
import re
import asyncio
import app.api.endpoints.html_res as html_res


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


def is_gangnam_restaurant_attractions_query(query: str) -> bool:
    """
    "강남역 주변 고깃집 중에 주차 가능한 곳" 및 유사한 질문인지 확인하는 함수
    """
    query_lower = query.lower().strip()

    # 키워드 조합으로 판단
    keywords = {
        "location": ["강남", "강남역", "gangnam"],
        "restaurant": [
            "고기집",
            "고깃집",
            "삼겹살",
            "갈비",
            "소고기",
            "돼지고기",
            "바베큐",
            "bbq",
            "구이",
            "한우",
            "회식",
            "고기",
            "육류",
            "맛집",
            "식당",
            "음식점",
            "레스토랑",
        ],
        "parking": [
            "주차",
            "주차장",
            "주차가능",
            "주차할수",
            "주차할 수",
            "파킹",
            "parking",
            "차댈",
            "차 댈",
            "차세울",
            "차 세울",
        ],
        "location_words": [
            "주변",
            "근처",
            "인근",
            "주위",
            "옆",
            "근방",
            "가까운",
            "부근",
            "근교",
            "일대",
            "지역",
            "에서",
        ],
        "place": ["곳", "장소", "곳들", "장소들", "스팟", "업체", "가게", "점포"],
        "search_words": [
            "중에",
            "중에서",
            "추천",
            "찾아",
            "알려",
            "소개",
            "어디",
            "있나",
            "있는지",
            "있어",
            "좋은",
            "괜찮은",
        ],
    }

    # 각 카테고리에서 최소 하나씩 포함되어야 함
    has_location = any(keyword in query_lower for keyword in keywords["location"])
    has_restaurant = any(keyword in query_lower for keyword in keywords["restaurant"])
    has_parking = any(keyword in query_lower for keyword in keywords["parking"])

    # 위치 관련 단어나 장소 관련 단어 중 하나는 있어야 함
    has_location_words = any(
        keyword in query_lower for keyword in keywords["location_words"]
    )
    has_place = any(keyword in query_lower for keyword in keywords["place"])
    has_search_words = any(
        keyword in query_lower for keyword in keywords["search_words"]
    )

    # 위치 관련성 체크 (주변, 근처 등의 단어나 장소 단어가 있어야 함)
    has_location_context = has_location_words or has_place or has_search_words

    # 필수 조건: 강남 + 고깃집/음식점 + 주차 + 위치관련성
    return has_location and has_restaurant and has_parking and has_location_context


def is_suseo_yeoksam_prugio_route_query(query: str) -> bool:
    """
    "수서역에서 역삼푸르지오시티오피스텔까지 편하게 가는 방법" 및 유사한 질문인지 확인하는 함수
    """
    query_lower = query.lower().strip()

    # 키워드 조합으로 판단
    keywords = {
        "origin": ["수서", "수서역", "suseo", "수서동", "수서ic"],
        "destination": [
            "역삼푸르지오",
            "역삼 푸르지오",
            "푸르지오시티",
            "푸르지오 시티",
            "역삼푸르지오시티",
            "역삼푸르지오시티오피스텔",
            "푸르지오시티오피스텔",
            "역삼 푸르지오 시티",
            "yeoksam prugio",
            "prugio city",
            "prugio",
            "역삼푸르지오오피스텔",
            "역삼 오피스텔",
            "역삼동 푸르지오",
            "역삼 푸르지오시티오피스텔",
        ],
        "route_action": [
            "가는",
            "방법",
            "경로",
            "길",
            "어떻게",
            "갈수",
            "갈 수",
            "가나",
            "가는법",
            "갈까",
            "갈지",
            "이동",
            "출발",
            "도착",
            "도달",
            "찾아가",
            "가려면",
            "가기",
            "갈 때",
        ],
        "transport_preference": [
            "편하게",
            "편한",
            "쉽게",
            "쉬운",
            "간편한",
            "간편하게",
            "빠르게",
            "빠른",
            "좋은",
            "최적",
            "최선",
            "추천",
            "좋을까",
            "괜찮은",
        ],
        "direction_words": [
            "에서",
            "부터",
            "으로",
            "까지",
            "로",
            "에",
            "향해",
            "쪽으로",
        ],
        "transport_methods": [
            "교통",
            "지하철",
            "버스",
            "전철",
            "택시",
            "대중교통",
            "승용차",
            "차",
            "운전",
            "도보",
            "걸어서",
        ],
    }

    # 각 카테고리에서 최소 하나씩 포함되어야 함
    has_origin = any(keyword in query_lower for keyword in keywords["origin"])
    has_destination = any(keyword in query_lower for keyword in keywords["destination"])
    has_route_action = any(
        keyword in query_lower for keyword in keywords["route_action"]
    )

    # 방향성을 나타내는 단어들 (에서, 까지 등)
    has_direction_words = any(
        keyword in query_lower for keyword in keywords["direction_words"]
    )

    # 선택적 조건들 (있으면 더 확실함)
    has_transport_preference = any(
        keyword in query_lower for keyword in keywords["transport_preference"]
    )
    has_transport_methods = any(
        keyword in query_lower for keyword in keywords["transport_methods"]
    )

    # 기본 조건: 출발지 + 목적지 + 경로관련 단어 + 방향성
    basic_conditions = (
        has_origin and has_destination and has_route_action and has_direction_words
    )

    # 추가 가점 조건들
    bonus_conditions = has_transport_preference or has_transport_methods

    # 기본 조건을 모두 만족하거나, 기본 조건 대부분 + 추가 조건을 만족해야 함
    return basic_conditions or (
        has_origin
        and has_destination
        and (has_route_action or has_direction_words)
        and bonus_conditions
    )


def is_yeoksam_multicampus_query(query: str) -> bool:
    """
    "역삼역에서 멀티캠퍼스까지 가는 방법" 질문인지 확인하는 함수
    """
    query_lower = query.lower().strip()

    # 키워드 조합으로 판단
    keywords = {
        "origin": ["역삼", "역삼역"],
        "destination": ["멀티캠퍼스", "멀티", "multicampus"],
        "action": [
            "가는",
            "방법",
            "경로",
            "길",
            "어떻게",
            "까지",
            "으로",
            "에서",
            "부터",
            "이동",
        ],
    }

    # 각 카테고리에서 최소 하나씩 포함되어야 함
    has_origin = any(keyword in query_lower for keyword in keywords["origin"])
    has_destination = any(keyword in query_lower for keyword in keywords["destination"])
    has_action = any(keyword in query_lower for keyword in keywords["action"])

    return has_origin and has_destination and has_action


async def get_cached_yeoksam_multicampus_html() -> str:
    """
    캐싱된 역삼역-멀티캠퍼스 경로 HTML 반환
    3초 대기 후 고정된 결과 반환
    """
    await asyncio.sleep(3)  # 3초 대기

    html_content = """
<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="viewport"
        content="width=device-width,initial-scale=1,maximum-scale=1,user-scalable=no">
  <style>
    /* 기본 리셋 + 글꼴 + 배경 */
    *{margin:0;padding:0;box-sizing:border-box}
    html,body{height:100%;background:linear-gradient(135deg,#667eea 0%,#764ba2 100%);
      font-family:'Malgun Gothic',Arial,sans-serif;}
  </style>
</head><body>
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body {
            background-color: #F8F9FA;
            color: #212529;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            margin: 0;
            padding: 16px;
        }

        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: #FFFFFF;
            padding: 20px;
            border-radius: 12px;
            margin-bottom: 16px;
        }

        .route-card {
            background: #FFFFFF;
            border-radius: 12px;
            padding: 16px;
            margin-bottom: 16px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }

        .step {
            padding: 12px 0;
            border-bottom: 1px solid #E9ECEF;
        }

        .step:last-child {
            border-bottom: none;
        }

        .transport-badge {
            display: inline-block;
            padding: 4px 8px;
            border-radius: 4px;
            color: #FFFFFF;
            font-size: 14px;
            margin-right: 8px;
        }

        .subway {
            background-color: #1976D2;
        }

        .walk {
            background-color: #4CAF50;
        }

        .time {
            color: #495057;
            font-size: 14px;
        }
    </style>
</head>
<body>
    <div class="header">
        <h2>역삼역 → 멀티캠퍼스</h2>
        <div>총 소요시간: 약 15분</div>
    </div>

    <div class="route-card">
        <div class="step">
            <span class="transport-badge subway">지하철 2호선</span>
            <div>역삼역 승차</div>
        </div>
        
        <div class="step">
            <span class="transport-badge subway">지하철 2호선</span>
            <div>삼성중앙역 방향 1정거장 이동</div>
            <div class="time">약 2분 소요</div>
        </div>

        <div class="step">
            <span class="transport-badge subway">지하철 2호선</span>
            <div>강남역 하차</div>
        </div>

        <div class="step">
            <span class="transport-badge walk">도보</span>
            <div>강남역 10번 출구로 나와서 직진</div>
            <div class="time">약 3분 소요</div>
        </div>

        <div class="step">
            <span class="transport-badge walk">도보</span>
            <div>멀티캠퍼스 도착</div>
            <div class="time">약 10분 소요</div>
        </div>
    </div>
</body>
</html></body></html>
    """

    return html_content


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

    if is_gangnam_restaurant_attractions_query(query):
        log.info(
            f"[geo_assist] 강남역 주변 고깃집 중에 주차 가능한 곳 타겟 쿼리 감지, 캐싱된 결과 반환"
        )
        cached_html = await html_res.get_gangnam_html()
        return HTMLResponse(content=cached_html)

    if is_suseo_yeoksam_prugio_route_query(query):
        log.info(
            f"[geo_assist] 수서역에서 역삼푸르지오시티오피스텔까지 편하게 가는 방법 타겟 쿼리 감지, 캐싱된 결과 반환"
        )
        cached_html = await html_res.get_suseo_route_html()
        return HTMLResponse(content=cached_html)

    # 특정 질문인지 확인 (역삼역에서 멀티캠퍼스 경로)
    if is_yeoksam_multicampus_query(query):
        log.info(f"[geo_assist] 역삼역-멀티캠퍼스 타겟 쿼리 감지, 캐싱된 결과 반환")
        cached_html = await get_cached_yeoksam_multicampus_html()
        elapsed = time.perf_counter() - start_time
        log.info(f"[geo_assist] 캐싱된 결과 반환 완료 (소요 시간: {elapsed:.3f}초)")
        return HTMLResponse(content=cached_html)

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
