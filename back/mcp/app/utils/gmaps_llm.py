"""
Google Maps 전용 LLM 래퍼 (Claude 3 버전)
1) 어떤 Maps-tool 을 쓸지 판단
2) raw 결과를 HTML 로 변환
"""

import os, json, logging, asyncio
from anthropic import AsyncAnthropic  # ⭐ Anthropic SDK
from dotenv import load_dotenv

load_dotenv()
log = logging.getLogger(__name__)

# Claude 3 모델 이름: haiku·sonnet·opus 중 선택
CLAUDE_MODEL = "claude-3-5-haiku-20241022"

client = AsyncAnthropic(api_key=os.getenv("CLAUDE_API_KEY"))

# ────────────────────────────── 공통 프롬프트
ROUTER_PROMPT = """
You are a router that maps user requests to **ONE** Google-Maps MCP tool call.

• If user just wants to know the nearest place, choose maps_search_places.
• If user wants a route, choose maps_directions.
• If you need coordinates for a landmark, call maps_geocode first.
Respond with JSON only: {"tool": "...", "arguments": { ... }}
If no tool is needed, respond with {"text": "<reply>"}.
"""

HTML_ONLY_PROMPT = """
You are an HTML-only designer.

Return a single HTML **fragment** (NO <html> or <body>) that looks like a
modern mobile card UI.  MUST include:

1. A colorful header with route title  (출발지 → 도착지 → 목적지명)
2. A gradient “summary card” (총 소요시간 · 거리 · 환승횟수)
3. Step cards with icons  🚶 / 🚇 / 🚌  + 소요시간
4. 정차역 전체 리스트  (작은 박스)
5. 노선 시각화 (도트·선, 시작/끝 색 구분)
6. 근처 추천 식당 3-4개 카드 (이름·거리·영업시간)
7. 요금·환승 뱃지

스타일 가이드:
• Pastel gradients (#ff6b6b, #74b9ff, etc.)
• Rounded-corner cards, subtle box-shadow
• Inline CSS so the fragment is self-contained
• Keep markup < 40 KB
• ABSOLUTELY NO explanatory text outside the fragment.
"""

PLACES_PROMPT = """
You are an HTML-only designer.

Create a neat, card-style list of the top places returned by the tool:
• Each card shows 🏦/🍽 icon, 이름, 거리, 주소, 평점
• Flexbox grid, soft drop-shadow, 650 px max-width
• Use pastel gradient header (#00b894→#55efc4) and rounded corners
• Inline CSS; no <html>/<body> wrapper; no explanations.
"""

# ────────────────────────────── 1) tool 선택
async def choose_tool(query: str, *, lat: float, lon: float) -> dict:
    user_msg = f"[USER LOCATION] lat={lat}, lon={lon}\n{query}"

    rsp = await client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=512,
        temperature=0.2,
        system=ROUTER_PROMPT,
        messages=[
            {"role": "user", "content": user_msg},
        ],
    )

    content = rsp.content[0].text.strip()
    log.debug("Router raw: %s", content)
    try:
        return json.loads(content)
    except Exception:
        return {"text": content}

# ────────────────────────────── 2) HTML 생성
async def to_html(
    rpc_result: dict,
    original_query: str,
    *,
    kind: str = "route",
) -> str:
    sys_prompt = PLACES_PROMPT if kind == "places" else HTML_ONLY_PROMPT
    tool_output = json.dumps(rpc_result, ensure_ascii=False, indent=2)

    rsp = await client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=1024,
        temperature=0.4,
        system=sys_prompt,
        messages=[
            {"role": "user", "content": original_query},
            {"role": "assistant", "content": tool_output},
        ],
    )

    html = rsp.content[0].text.strip()
    # 줄바꿈·중복 공백 제거 → 한 줄 fragment
    return " ".join(html.split())
