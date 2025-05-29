import os, json, logging, asyncio
import re
from anthropic import AsyncAnthropic
from dotenv import load_dotenv
import html
load_dotenv()
log = logging.getLogger(__name__)

# ────────────────────────────── 모델 설정
ROUTER_MODEL = "claude-3-5-haiku-20241022"
HTML_MODEL   = "claude-3-5-sonnet-20241022"

client = AsyncAnthropic(api_key=os.getenv("CLAUDE_API_KEY"))

# ────────────────────────────── 공통 프롬프트
ROUTER_PROMPT = """
You are a router that maps user requests to **ONE** Google-Maps MCP tool call.
• If user just wants to know the nearest place, choose maps_search_places.
• If user wants a route, choose maps_directions.
• If you need coordinates for a landmark, call maps_geocode first.
If no tool is needed, respond with {"text": "<reply>"}.
Respond with JSON only: {"tool":"…","arguments":{…}}

# 🇰🇷 반드시 아래 두 파라미터를 arguments 에 포함해라
#    "language":"ko", "region":"KR"
"""
HTML_ONLY_PROMPT = """
• 절대 JSON 문자열처럼 HTML을 주지 마. "\\n", "\\", "\"" 문자가 없어야 하고, 순수 HTML 코드 그 자체를 출력해.
• 응답은 {"text": "<html>...</html>"} 같은 JSON 형태로 절대 반환하지 마.
• HTML은 JSON 문자열로 감싸지 말고, 말 그대로 HTML 태그 그대로 출력해.

너는 HTML-only 디자이너야.
반드시 **한글**로만 작성하고, 아래 예시 같은 모바일 카드 UI 전체 페이지를 반환해.
(반드시 <!doctype html> ~ </html> 까지 포함)

필수 요소
1. 파스텔 그라디언트 헤더  ─ 제목(출발지 → 도착지 → 목적지)
2. 그라디언트 요약 카드    ─ 총 소요시간 · 거리 · 환승횟수
3. 단계 카드(🚶/🚇/🚌)      ─ 단계 제목 + 설명 + 소요시간
4. 정차역 리스트            ─ 박스 내부에 작게
5. 노선 시각화              ─ 점·선, 시작/끝 색 구분
6. 근처 추천 식당 3~4곳     ─ 이름·거리·영업시간
7. 요금·환승 뱃지

스타일 가이드
• 예시 HTML과 비슷한 컬러 팔레트 사용 ( #ff6b6b, #ee5a24, #00b894, #74b9ff 등 )
• ‘Malgun Gothic’를 기본 글꼴로 지정
• 카드·배지·아이콘 등은 둥근 모서리 + box-shadow
• 전체 마크업 40 KB 이하
• 해설·주석 X, 오직 완전한 HTML만 출력
"""
PLACES_PROMPT = """
• 절대 JSON 문자열처럼 HTML을 주지 마. "\\n", "\\", "\"" 문자가 없어야 하고, 순수 HTML 코드 그 자체를 출력해.
• 응답은 {"text": "<html>...</html>"} 같은 JSON 형태로 절대 반환하지 마.
• HTML은 JSON 문자열로 감싸지 말고, 말 그대로 HTML 태그 그대로 출력해.
너는 HTML-only 디자이너야. 아래의 장소 정보를 참고해서 아름답고 직관적인 모바일 UI를 만들어줘.

[디자인 요구]
• 전체 HTML을 반환해 (반드시 <!DOCTYPE html>부터 </html>까지 포함)
• 모바일 기준, 전체 폭 650px 이하로
• 상단에 파스텔 그라디언트 배경을 가진 헤더 카드 포함 (예: #667eea → #764ba2)
• 각각의 장소 정보를 카드로 나열
• 각 카드 구성:
  - 🍽 이름 (크게, 굵게)
  - 📍 위치 요약 (예: '성수동, 서울숲역 도보 5분')
  - 🏠 주소 (조금 작게)
  - ⭐ 평점 (노란색 강조)

[스타일 가이드]
• `Malgun Gothic` 폰트 사용
• 전체 배경은 부드러운 그라디언트 (#667eea → #764ba2)
• 각 카드 배경은 white, 그림자 + 라운드 처리
• 카드 간 간격은 충분히 줘 (margin/gap)
• 색상은 파스텔 톤으로만 (노란색, 보라색, 하늘색 등)
• 절대 설명이나 주석은 넣지 말고, 완전한 HTML만 출력해
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
async def choose_tool(query: str, *, lat: float, lon: float) -> dict:
    user_msg = (
        f"사용자의 현재 위치는 위도 {lat}, 경도 {lon}입니다.\n"
        f"이 위치를 참고해서 경로 또는 장소 정보를 알려주세요.\n"
        f"사용자 요청: {query}"
    )

    rsp = await client.messages.create(
        model=ROUTER_MODEL,
        max_tokens=512,
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
            # ✅ fallback: location 정보 추가
            if "location" not in data["arguments"]:
                data["arguments"]["location"] = {"latitude": lat, "longitude": lon}
        return data
    except Exception:
        return {"text": content}


# ────────────────────────────── 2) HTML 생성
async def to_html(
    rpc_result: dict,
    original_query: str,
    *, kind: str = "route",
) -> str:
    sys_prompt = PLACES_PROMPT if kind == "places" else HTML_ONLY_PROMPT
    tool_output = json.dumps(rpc_result, ensure_ascii=False, indent=2)

    rsp = await client.messages.create(
        model=HTML_MODEL,
        max_tokens=1200,
        temperature=0.4,
        system=sys_prompt,
        messages=[
            {"role": "user", "content": original_query},
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


