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

🗣️ 자연어 경로 요청 패턴 인식:
다음과 같은 모든 패턴을 경로 요청으로 인식하세요:
- "A에서 B로/까지 가는 방법"
- "A에서 B 가는법" 
- "B로/에 가는 방법" (출발지 미지정)
- "B 어떻게 가나요/가나" 
- "B 가는 길"
- "B 경로 알려줘"
- "B 교통편"
- "A부터 B까지"
- "A 출발해서 B"
- 기타 이동/교통 관련 모든 표현

🎯 경로 요청 처리 규칙:
1. 위 패턴 중 하나라도 해당되면 → maps_directions 사용
2. 출발지 명시 없으면 → current_address를 origin으로 사용
3. 출발지 명시 있으면 → 해당 장소를 origin으로 사용
4. 반드시 mode는 "transit"으로 설정 (대중교통)

✔️ 기타 도구 사용 경우:
- 장소 검색: "근처 맛집", "주변 카페", "A 찾아줘" 등
- 주소 변환: "여기가 어디야", "이 위치 주소" 등

🏷️ 매개변수 설정:
- language: "ko"
- region: "KR" 
- mode: "transit" (경로 요청 시)

Return **JSON only**: {"tool":"<tool_name>","arguments":{…}}

중요: 한국어 자연어의 다양한 경로 표현을 모두 인식하여 정확한 길찾기를 제공하세요.
"""

HTML_ONLY_PROMPT = """
- 절대 JSON 문자열처럼 HTML을 주지 마. 순수 HTML 코드 그 자체를 출력해.

안드로이드 웹뷰 전용 대중교통 경로 UI 디자이너야.

🎨 필수 색상 대비 규칙:
- 배경색과 글자색 대비비 최소 4.5:1 이상 보장
- 기본 배경: #F8F9FA (연한 회색)
- 기본 글자: #212529 (진한 검정)
- 카드 배경: #FFFFFF (순백)
- 헤더 배경: linear-gradient(135deg, #667eea 0%, #764ba2 100%)
- 헤더 글자: #FFFFFF (순백) - 그라디언트 위에서만

⚠️ 색상 안전 규칙:
- 절대 같은 계열 색상을 배경-글자로 사용 금지
- 회색 배경에는 반드시 검은색 계열 글자
- 어두운 배경에는 반드시 밝은색 글자
- 투명도 사용 시 최종 대비비 계산 후 적용

🎯 명확한 색상 시스템:
- Primary: #1976D2 (파랑) / 흰 배경에서만
- Success: #4CAF50 (초록) / 흰 배경에서만  
- Warning: #FF9800 (주황) / 흰 배경에서만
- Error: #F44336 (빨강) / 흰 배경에서만
- 모든 컬러 배경에는 white 또는 #FFFFFF 글자만

📱 레이아웃 필수사항:
1. 전체 배경: #F8F9FA
2. 카드들: 흰색 배경 + 검은색 글자
3. 헤더만: 그라디언트 + 흰색 글자
4. 버튼: 컬러 배경 + 흰색 글자

🚨 절대 경로를 압축하지 말고 모든 구간의 모든 단계를 표시하세요.
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
- 액션: 네이버지도 링크 버튼만 제공
- 아이콘: 📍🌟🗺️⏰

🔗 링크 처리:
- 네이버지도: https://map.naver.com/v5/search/장소명 형식으로 링크
- 장소명에 특수문자가 있으면 URL 인코딩 적용
- 버튼 텍스트: "네이버지도에서 보기" 또는 "지도보기"

💡 안드로이드 웹뷰 특화:
- JavaScript 최소화
- CSS transform으로 부드러운 애니메이션
- touch-action: manipulation으로 300ms 지연 제거

⚠️ 제외 요소:
- 전화번호 링크 및 전화 관련 기능 제거
- 📞 아이콘 사용하지 않음
- tel: 링크 사용하지 않음
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

    max_retries = 3
    for attempt in range(max_retries):
        try:
            rsp = await client.messages.create(
                model=ROUTER_MODEL,
                max_tokens=1024,
                temperature=0.2,
                system=ROUTER_PROMPT,
                messages=[{"role": "user", "content": user_msg}],
            )
            break
        except Exception as e:
            log.warning(f"Claude API 호출 시도 {attempt + 1} 실패: {e}")
            if attempt == max_retries - 1:
                # fallback 응답
                return {"text": "서비스가 일시적으로 불안정합니다. 잠시 후 다시 시도해주세요."}
            await asyncio.sleep(2 ** attempt)

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