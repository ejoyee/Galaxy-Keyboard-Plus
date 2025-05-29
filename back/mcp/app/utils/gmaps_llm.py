"""
OpenAI 프롬프트를 Google Maps 용도로만 단순화한 래퍼
1) 어떤 Maps-tool 을 쓸지 판단
2) raw 결과를 HTML / 텍스트로 요약
"""

import os, json, logging
from openai import AsyncOpenAI
from dotenv import load_dotenv

load_dotenv()
log = logging.getLogger(__name__)
client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

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
• Google-like pastel gradients (#ff6b6b, #74b9ff, etc.)
• Rounded-corner cards, subtle box-shadow
• Use inline CSS so the fragment is self-contained
• Keep markup < 40 KB
• ABSOLUTELY NO explanatory text outside the fragment.
"""

# ───── 장소 리스트용 ─────────────────────────────────────
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
    user = f"[USER LOCATION] lat={lat}, lon={lon}\n{query}"
    rsp = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": ROUTER_PROMPT},
            {"role": "user", "content": user},
        ],
        max_tokens=512,
    )
    msg = rsp.choices[0].message.content.strip()
    log.debug("Router raw: %s", msg)
    try:
        return json.loads(msg)
    except Exception:
        return {"text": msg}

# ────────────────────────────── 2) 요약
async def to_html(
    rpc_result: dict,
    original_query: str,
    *,
    kind: str = "route",
) -> str:
    if kind == "places":
        sys_prompt = PLACES_PROMPT
    else:  # route
        sys_prompt = HTML_ONLY_PROMPT
    txt = json.dumps(rpc_result, ensure_ascii=False, indent=2)
    rsp = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": original_query},
            {"role": "assistant", "content": txt},
        ],
        max_tokens=1024,
        temperature=0.4,
    )
    return " ".join(rsp.choices[0].message.content.strip().split())
