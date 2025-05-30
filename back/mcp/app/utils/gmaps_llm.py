import os, json, logging, asyncio
import re
from anthropic import AsyncAnthropic
from dotenv import load_dotenv
import html
load_dotenv()
log = logging.getLogger(__name__)

# ────────────────────────────── 모델 설정
ROUTER_MODEL = "claude-3-5-haiku-20241022"
# ROUTER_MODEL = "claude-3-5-sonnet-20241022"
HTML_MODEL   = "claude-3-5-sonnet-20241022"

client = AsyncAnthropic(api_key=os.getenv("CLAUDE_API_KEY"))

# ────────────────────────────── 공통 프롬프트
ROUTER_PROMPT = """
You are a router that maps user requests to **ONE** Google-Maps MCP tool call.

✔️ You may freely choose **any** Google-Maps MCP tool available, such as
maps_search_places, maps_directions, maps_geocode, maps_place_details,
maps_nearby_search, maps_distance_matrix, etc.
Pick the single tool that best satisfies the user's request.

🏷️ Location handling rules for directions/routes:
• If the user requests directions/routes and does NOT specify an origin,
  use the provided current_address as the origin (this is already converted from coordinates).
• If the user specifies a different starting point, use that instead.
• Always ensure the full route is captured by using complete address information.

🏷️ Location handling rules for search/places:
• If the request mentions any city, district, station, or landmark, 
  rely on that textual location only.
• Use the caller's coordinates only when no location clue exists at all.

If no tool is needed, reply with {"text": "<reply>"}.

Return **JSON only** as
{"tool":"<tool_name>","arguments":{…}}  — no extra keys, no commentary.

🇰🇷 반드시 아래 두 파라미터를 arguments 에 포함해라
"language":"ko", "region":"KR"

중요: 경로/길찾기 요청의 경우 전체 경로가 표시되도록 완전한 주소 정보를 사용하세요.
"""

HTML_ONLY_PROMPT = """
- 절대 JSON 문자열처럼 HTML을 주지 마. "\\n", "\\", "\"" 문자가 없어야 하고, 순수 HTML 코드 그 자체를 출력해.
- 응답은 {"text": "<html>...</html>"} 같은 JSON 형태로 절대 반환하지 마.

너는 안드로이드 웹뷰 전용 HTML 디자이너야.
반드시 **한글**로만 작성하고, 모바일 최적화된 대중교통 경로 UI를 만들어줘.

🚨 안드로이드 웹뷰 최적화 요구사항:
- viewport: width=device-width, initial-scale=1.0, user-scalable=no
- 터치 친화적: 최소 44px 터치 영역, 충분한 간격
- 스크롤 최적화: -webkit-overflow-scrolling: touch
- 폰트: system-ui, -apple-system, 'Malgun Gothic' fallback
- 다크모드 대응: @media (prefers-color-scheme: dark)

🎨 디자인 시스템:
- 컬러: Material Design 3 기반 (Primary: #1976D2, Surface: #F5F5F5)
- 그림자: box-shadow 대신 border + background로 성능 최적화
- 애니메이션: transform 사용, 60fps 보장
- 아이콘: 유니코드 이모지 활용 (🚇🚌🚶‍♀️⏰📍)

📱 레이아웃 구조:
1. 고정 헤더 (sticky) - 출발지→도착지, 총 시간/거리
2. 스크롤 가능한 메인 영역:
   - 요약 카드 (시간, 거리, 요금, 환승)
   - 단계별 카드들 (아이콘 + 설명 + 시간)
   - 상세 정보 (정차역, 노선도)
3. 하단 여백 (safe-area-inset-bottom 대응)

🚀 성능 최적화:
- CSS는 <style> 태그 내부에 inline으로
- 외부 리소스 로딩 금지
- 이미지 대신 CSS 그라디언트/도형 활용
- 복잡한 CSS 선택자 지양

🎯 UX 최적화:
- 로딩 없이 즉시 표시
- 중요 정보 우선 배치 (소요시간, 환승횟수)
- 색상으로 노선 구분 (지하철 1호선=파랑, 2호선=초록 등)
- 단계별 진행 표시기

⚠️ 절대 경로를 압축하지 말고 모든 구간의 모든 단계를 표시하세요.
"""

PLACES_PROMPT = """
- 절대 JSON 문자열처럼 HTML을 주지 마. 순수 HTML 코드만 출력해.

안드로이드 웹뷰 전용 장소 검색 결과 UI를 만들어줘.

📱 안드로이드 웹뷰 최적화:
- 터치 최적화: 카드는 최소 56dp(약 56px) 높이
- 스와이프 스크롤: smooth scrolling 적용
- 네이티브 느낌: Material Design 3 가이드라인 준수
- 성능: 하드웨어 가속 활용 (transform3d, will-change)

🎨 디자인 가이드:
- 카드 기반 레이아웃 (elevation 2-4dp)
- 라운드 코너: 12px (안드로이드 스타일)
- 색상: #1976D2(Primary), #FFC107(Rating), #4CAF50(Open)
- 타이포그래피: 16sp(제목), 14sp(본문), 12sp(보조)

🏪 장소 카드 구성:
- 헤더: 이름 + 평점 + 영업상태
- 본문: 주소 + 카테고리 + 거리
- 액션: 전화걸기, 길찾기, 네이버지도 버튼
- 아이콘: 📍🌟📞🗺️⏰

🔗 링크 처리:
- tel: 링크로 전화 연결
- 네이버지도: nmap://place?lat=&lng= 형식
- 구글지도: geo: 링크 활용

💡 안드로이드 웹뷰 특화:
- JavaScript 최소화
- CSS transform으로 부드러운 애니메이션
- touch-action: manipulation으로 300ms 지연 제거
"""


HTML_SHELL_HEAD = """<!doctype html>
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
"""
HTML_SHELL_TAIL = "</body></html>"


# ────────────────────────────── 1) tool 선택
async def choose_tool(query: str, *, lat: float, lon: float, current_address: str = None) -> dict:
    user_msg_parts = [
        f"사용자의 현재 위치는 위도 {lat}, 경도 {lon}입니다."
    ]
    
    if current_address:
        user_msg_parts.append(f"현재 위치의 주소는 '{current_address}' 입니다.")
        user_msg_parts.append(f"경로/길찾기 요청인 경우 이 주소를 출발지로 사용해주세요.")
    else:
        user_msg_parts.append(f"출발지 명시가 없을 경우 사용자의 현재 좌표를 출발지로 사용해주세요.")
    
    user_msg_parts.extend([
        f"반드시 전체 경로의 모든 구간을 표시하도록 해주세요.",
        f"사용자 요청: {query}"
    ])
    
    user_msg = "\n".join(user_msg_parts)

    rsp = await client.messages.create(
        model=ROUTER_MODEL,
        max_tokens=1024,
        temperature=0.2,
        system=ROUTER_PROMPT,
        messages=[{"role": "user", "content": user_msg}],
    )

    content = rsp.content[0].text.strip()
    log.debug("Router raw: %s", content)

    try:
        data = json.loads(content)
        if "arguments" in data:
            data["arguments"].setdefault("language", "ko")
            data["arguments"].setdefault("region", "KR")
            # ✅ fallback: location 정보 추가 (search의 경우)
            if data.get("tool") == "maps_search_places" and "location" not in data["arguments"]:
                data["arguments"]["location"] = {"latitude": lat, "longitude": lon}
        return data
    except Exception:
        return {"text": content}


# ────────────────────────────── 2) HTML 생성
async def to_html(
    rpc_result: dict,
    original_query: str,
    *, 
    kind: str = "route",
    origin_info: dict = None,
) -> str:
    sys_prompt = PLACES_PROMPT if kind == "places" else HTML_ONLY_PROMPT
    
    # 경로 정보와 출발지 정보를 포함한 컨텍스트 구성
    context_parts = [original_query]
    
    if origin_info:
        context_parts.append(f"출발지 정보: {origin_info.get('address', '')} ({origin_info.get('coordinates', '')})")
    
    if kind == "route":
        context_parts.append("전체 경로의 모든 구간과 단계를 빠짐없이 표시해주세요.")
    
    context_msg = "\n".join(context_parts)
    tool_output = json.dumps(rpc_result, ensure_ascii=False, indent=2)

    rsp = await client.messages.create(
        model=HTML_MODEL,
        max_tokens=1500,  # 전체 경로 표시를 위해 토큰 수 증가
        temperature=0.4,
        system=sys_prompt,
        messages=[
            {"role": "user", "content": context_msg},
            {"role": "assistant", "content": tool_output},
        ],
    )

    # ✅ 안전하게 content 접근
    if not rsp.content or len(rsp.content) == 0:
        raise ValueError("Claude 응답이 비어있습니다 (rsp.content = []).")

    raw_html_str = rsp.content[0].text.strip()
    if raw_html_str.startswith("{") and raw_html_str.endswith("}"):
        decoded = json.loads(raw_html_str)
        raw_html_str = decoded if isinstance(decoded, str) else ""

    return raw_html_str