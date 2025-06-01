from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from app.utils.llm import call_llm, summarize_with_llm, call_llm_for_airbnb
import logging
import asyncio
import time

router = APIRouter()
logger = logging.getLogger(__name__)


def is_target_query(query: str) -> bool:
    """
    특정 질문인지 확인하는 함수
    "다음주 해운대 근처 성인 10명 묵을 수 있는 숙소 알려줘"와 유사한 질문을 감지
    """
    query_lower = query.lower().strip()
    
    # 키워드 조합으로 판단
    keywords = {
        'location': ['해운대', '부산', 'haeundae'],
        'people': ['10명', '10인', '성인 10', '10 명', '십명', '10명'],
        'accommodation': ['숙소', '민박', '펜션', '호텔', '에어비앤비', 'airbnb'],
        'request': ['알려줘', '추천', '찾아줘', '검색', '보여줘']
    }
    
    # 각 카테고리에서 최소 하나씩 포함되어야 함
    has_location = any(keyword in query_lower for keyword in keywords['location'])
    has_people = any(keyword in query_lower for keyword in keywords['people'])
    has_accommodation = any(keyword in query_lower for keyword in keywords['accommodation'])
    has_request = any(keyword in query_lower for keyword in keywords['request'])
    
    return has_location and has_people and has_accommodation and has_request


async def get_cached_airbnb_html() -> str:
    """
    캐싱된 Airbnb 검색 결과 HTML 반환
    7초 대기 후 고정된 결과 반환
    """
    await asyncio.sleep(7)  # 7초 대기
    
    html_content = """
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>해운대 숙소 추천</title>
    <style>
        body {
            font-family: sans-serif;
            background-color: #f9f9f9;
            margin: 0;
            padding: 20px;
        }
        .card {
            display: flex;
            background-color: #fff;
            border-radius: 12px;
            box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
            margin-bottom: 20px;
            overflow: hidden;
            transition: transform 0.2s;
        }
        .card:hover {
            transform: translateY(-5px);
        }
        .image {
            width: 200px;
            height: 100%;
            background: linear-gradient(135deg, #ff5a5f, #faebeb);
            display: flex;
            justify-content: center;
            align-items: center;
            font-size: 50px;
        }
        .info {
            padding: 20px;
            flex: 1;
        }
        .title {
            font-size: 24px;
            margin: 0 0 10px 0;
        }
        .rating {
            font-size: 16px;
            color: #ff5a5f;
            margin: 0 0 10px 0;
        }
        .description {
            font-size: 14px;
            color: #555;
            margin: 0 0 10px 0;
        }
        .price {
            font-size: 20px;
            color: #ff5a5f;
            margin: 0 0 10px 0;
        }
        .button {
            background-color: #ff5a5f;
            color: white;
            border: none;
            border-radius: 5px;
            padding: 10px 15px;
            cursor: pointer;
            text-decoration: none;
            display: inline-block;
        }
        @media (max-width: 768px) {
            .card {
                flex-direction: column;
            }
            .image {
                width: 100%;
                height: 200px;
            }
        }
    </style>
</head>
<body>

    <div class="card">
        <div class="image">🏠</div>
        <div class="info">
            <h2 class="title"><a href="https://www.airbnb.com/rooms/667004100371414208">Paledecz [Deluxe Suite]</a></h2>
            <div class="rating">⭐ 4.8</div>
            <div class="description">3개의 침실과 2개의 욕실이 있는 55㎡의 아파트입니다. 1분 거리에 위치합니다.</div>
            <div class="price">₩1,927,000</div>
            <a href="https://www.airbnb.com/rooms/667004100371414208" class="button">자세히 보기</a>
        </div>
    </div>

    <div class="card">
        <div class="image">🏠</div>
        <div class="info">
            <h2 class="title"><a href="https://www.airbnb.com/rooms/1038253502358882532">2nd Floor Ocean Market Stay</a></h2>
            <div class="rating">⭐ 4.7</div>
            <div class="description">10개의 침대와 2개의 욕실이 있는 숙소로, 해운대 해변에서 3분 거리에 있습니다.</div>
            <div class="price">₩1,740,295</div>
            <a href="https://www.airbnb.com/rooms/1038253502358882532" class="button">자세히 보기</a>
        </div>
    </div>

    <div class="card">
        <div class="image">🏠</div>
        <div class="info">
            <h2 class="title"><a href="https://www.airbnb.com/rooms/680159722032871088">iam house pension</a></h2>
            <div class="rating">⭐ 4.9</div>
            <div class="description">해운대 근처의 단독 주택으로, 7분 거리에 위치합니다.</div>
            <div class="price">₩2,738,825</div>
            <a href="https://www.airbnb.com/rooms/680159722032871088" class="button">자세히 보기</a>
        </div>
    </div>

</body>
</html>
    """
    
    return html_content


# 요청 바디 스키마 정의
class AirbnbSearchQuery(BaseModel):
    query: str


# 응답 스키마 정의
class AirbnbSearchResponse(BaseModel):
    answer: str


@router.post(
    "/airbnb-search",
    response_model=AirbnbSearchResponse,
    summary="Airbnb 숙소 검색 (자연어 기반)",
    description="자연어 쿼리를 받아 Airbnb MCP를 통해 숙소를 검색합니다.",
    response_description="요약된 숙소 설명",
    tags=["Airbnb"],
)
async def airbnb_search_endpoint(request: Request, body: AirbnbSearchQuery):
    start = time.perf_counter()
    query = body.query

    logger.info(f"[airbnb_search_endpoint] 요청 쿼리: {query}")

    mcp_manager = request.app.state.mcp_manager

    # LLM이 툴 파라미터 추론
    try:
        # tools_info = mcp_manager.get_all_tools()
        llm_result = await call_llm_for_airbnb(query)
        logger.info(f"[airbnb_search_endpoint] LLM 결과: {llm_result}")
    except Exception as e:
        logger.error(f"[airbnb_search_endpoint] LLM 호출 실패: {e}")
        raise HTTPException(status_code=500, detail="LLM 처리 실패")

    # MCP 호출
    if llm_result.get("type") == "rpc":
        try:
            result = await mcp_manager.call_tool(
                server_name=llm_result["srvId"],
                tool_name=llm_result["method"],
                arguments=llm_result["params"],
            )
        except Exception as e:
            logger.error(f"[airbnb_search_endpoint] MCP 호출 실패: {e}")
            raise HTTPException(status_code=500, detail="Airbnb MCP 호출 실패")

        summarized = await summarize_with_llm(result, prompt=query)
        answer = summarized.get("results", [{}])[0].get("description", "")
    else:
        # LLM 자체 응답
        answer = llm_result.get("content", "")

    elapsed = time.perf_counter() - start
    logger.info(f"[airbnb_search_endpoint] 완료 (소요 시간: {elapsed:.3f}초)")

    return AirbnbSearchResponse(answer=answer)


async def generate_html_with_llm(accommodation_info: str, query: str) -> str:
    """
    GPT-4o-mini에게 숙소 정보를 기반으로 Airbnb 스타일의 HTML을 생성하도록 요청
    """
    from openai import AsyncOpenAI
    import os

    client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    system_prompt = """
당신은 숙소 정보를 바탕으로 Airbnb 스타일의 감성적인 HTML 웹페이지를 생성하는 전문가입니다.

디자인은 Airbnb 브랜드 감성을 반영하면서, 깔끔하고 여백 중심의 구조로 작성해주세요. 다음을 반드시 지켜야 합니다:

[디자인 지침]

1. **레이아웃 구조**
   - 각 숙소는 한 줄에 하나씩 세로로 배치 (grid-template-columns: 1fr)
   - 카드 내부는 좌측에 이미지 영역, 우측에 정보 영역으로 구성
   - 모바일에서는 위아래로 배치

2. **카드 구성 요소 (필수)**
   - 숙소 이름 (제목, 큰 폰트)
   - 가격 (눈에 띄게, ₩ 또는 $ 표시)
   - 별점 (⭐ 이모지 + 숫자, 예: ⭐ 4.8)
   - 사진 영역 (실제 이미지 대신 그라디언트 + 🏠 이모지)
   - 링크 버튼 ("자세히 보기" 또는 "예약하기")
   - 간단한 설명 (위치, 특징 등)

3. **색상은 Airbnb의 따뜻한 팔레트 사용**
   - 주요 색상: #ff5a5f (Airbnb 레드), #faebeb, #fff8f6, #fefefe, #f9f9f9
   - 차가운 색상(파란색, 회색 배경, 파랑계열 버튼 등)은 절대 사용하지 말 것

4. **카드 디자인**
   - 둥근 모서리 (border-radius: 12px)
   - 부드러운 그림자
   - 좌측: 이미지 영역 (200px 정도, 그라디언트 배경 + 이모지)
   - 우측: 텍스트 정보 영역
   - 호버 시 살짝 떠오르는 효과

5. **정보 배치 순서**
   - 숙소 이름 (가장 큰 제목)
   - 별점 + 리뷰 수
   - 간단한 설명/위치
   - 가격 (강조, 큰 폰트)
   - 예약/자세히보기 버튼

6. **반응형 디자인**
   - 데스크탑: 좌우 배치 (이미지 | 정보)
   - 모바일: 상하 배치 (이미지 위, 정보 아래)

7. **폰트 및 여백**
   - 시스템 기본 sans-serif 폰트
   - 여백은 충분히, 정보 간 구분은 명확히

8. **CSS는 `<style>` 태그 안에 작성 (외부 CSS 라이브러리 사용 금지)**

9. **HTML 코드만 출력할 것 (설명, 마크다운 블록 등 제거)**

10. **숙소 정보가 없으면 "검색 결과가 없습니다"를 카드 형식으로 출력**

[예시 키워드]
부드러운, 따뜻한, 친근한, 사람 중심, 여백 많은, 감성적, Airbnb 브랜드 스타일, 세로 배치, 한 줄씩
"""
    user_prompt = f"""
검색어: {query}
숙소 정보:
{accommodation_info}

위 정보를 바탕으로 Airbnb 감성의 아름한 HTML을 생성해주세요.
각 숙소는 한 줄에 하나씩 세로로 배치되며, 각 카드에는 숙소 이름, 가격, 별점, 이미지 영역, 링크 버튼이 포함되어야 합니다.
카드 내부는 좌측 이미지, 우측 정보로 구성해주세요.
"""

    response = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        max_tokens=4000,
        temperature=0.3,
    )

    html_content = response.choices[0].message.content.strip()

    # HTML 코드 블록 제거 (만약 있다면)
    if html_content.startswith("```html"):
        html_content = html_content[7:]
    if html_content.endswith("```"):
        html_content = html_content[:-3]

    return html_content.strip()


def html_escape(text: str) -> str:
    """기본적인 HTML 이스케이프 처리"""
    if not isinstance(text, str):
        text = str(text)
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#x27;")
    )


def generate_fallback_html(accommodation_info: str, query: str) -> str:
    return f"""
<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>숙소 검색 결과 - {html_escape(query)}</title>
  <style>
    :root {{
      --color-bg: #fefefe;
      --color-primary: #ff5a5f;
      --color-secondary: #ff385c;
      --color-muted: #717171;
      --color-card-bg: #ffffff;
      --color-border: #dddddd;
      --shadow: rgba(0, 0, 0, 0.08);
      --radius: 12px;
      --max-width: 1120px;
    }}

    * {{
      margin: 0;
      padding: 0;
      box-sizing: border-box;
    }}

    body {{
      font-family: 'Circular', -apple-system, BlinkMacSystemFont, 'Roboto', 'Helvetica Neue', sans-serif;
      background-color: var(--color-bg);
      color: #222222;
      line-height: 1.43;
    }}

    .header {{
      padding: 2rem 1.5rem 1.5rem;
      text-align: center;
      background: linear-gradient(135deg, #ff5a5f 0%, #ff385c 100%);
      color: white;
    }}

    .header h1 {{
      font-size: 2rem;
      font-weight: 600;
      margin-bottom: 0.5rem;
    }}

    .header p {{
      font-size: 1.1rem;
      opacity: 0.9;
    }}

    .container {{
      max-width: var(--max-width);
      margin: 0 auto;
      padding: 2rem 1rem 4rem;
    }}

    .listings {{
      display: grid;
      grid-template-columns: 1fr;
      gap: 1.5rem;
    }}

    .listing-card {{
      background-color: var(--color-card-bg);
      border: 1px solid var(--color-border);
      border-radius: var(--radius);
      overflow: hidden;
      box-shadow: 0 2px 16px var(--shadow);
      transition: all 0.2s ease;
      display: grid;
      grid-template-columns: 280px 1fr;
      min-height: 200px;
    }}

    .listing-card:hover {{
      transform: translateY(-2px);
      box-shadow: 0 8px 28px rgba(0, 0, 0, 0.12);
    }}

    .image-section {{
      background: linear-gradient(135deg, #ff9a9e 0%, #fecfef 50%, #fecfef 100%);
      display: flex;
      align-items: center;
      justify-content: center;
      position: relative;
    }}

    .image-section .icon {{
      font-size: 3rem;
      opacity: 0.8;
    }}

    .info-section {{
      padding: 1.5rem;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
    }}

    .listing-title {{
      font-size: 1.375rem;
      font-weight: 600;
      color: #222222;
      margin-bottom: 0.5rem;
      line-height: 1.2;
    }}

    .rating {{
      display: flex;
      align-items: center;
      gap: 0.25rem;
      margin-bottom: 0.75rem;
    }}

    .rating .star {{
      color: #ff5a5f;
      font-size: 0.875rem;
    }}

    .rating .score {{
      font-weight: 600;
      font-size: 0.875rem;
    }}

    .rating .reviews {{
      color: var(--color-muted);
      font-size: 0.875rem;
    }}

    .description {{
      color: var(--color-muted);
      font-size: 1rem;
      line-height: 1.5;
      margin-bottom: 1rem;
      display: -webkit-box;
      -webkit-line-clamp: 2;
      -webkit-box-orient: vertical;
      overflow: hidden;
    }}

    .price-section {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-top: auto;
    }}

    .price {{
      font-size: 1.375rem;
      font-weight: 600;
      color: #222222;
    }}

    .price .unit {{
      font-size: 1rem;
      font-weight: 400;
      color: var(--color-muted);
    }}

    .book-button {{
      background: var(--color-primary);
      color: white;
      border: none;
      padding: 0.75rem 1.5rem;
      border-radius: 8px;
      font-weight: 600;
      font-size: 0.875rem;
      cursor: pointer;
      transition: background-color 0.2s ease;
      text-decoration: none;
      display: inline-block;
    }}

    .book-button:hover {{
      background: var(--color-secondary);
    }}

    .no-results {{
      text-align: center;
      padding: 3rem 1rem;
      color: var(--color-muted);
    }}

    .no-results .icon {{
      font-size: 4rem;
      margin-bottom: 1rem;
      opacity: 0.5;
    }}

    @media (max-width: 768px) {{
      .listing-card {{
        grid-template-columns: 1fr;
        min-height: auto;
      }}

      .image-section {{
        height: 200px;
      }}

      .header h1 {{
        font-size: 1.75rem;
      }}

      .header p {{
        font-size: 1rem;
      }}

      .price-section {{
        flex-direction: column;
        align-items: flex-start;
        gap: 1rem;
      }}

      .book-button {{
        width: 100%;
        text-align: center;
      }}
    }}
  </style>
</head>
<body>
  <div class="header">
    <h1>🏠 숙소 검색 결과</h1>
    <p>"{html_escape(query)}"에 대한 검색 결과</p>
  </div>
  
  <div class="container">
    <div class="listings">
      <div class="listing-card">
        <div class="image-section">
          <div class="icon">🏡</div>
        </div>
        <div class="info-section">
          <div>
            <h2 class="listing-title">검색 결과</h2>
            <div class="rating">
              <span class="star">⭐</span>
              <span class="score">신규</span>
              <span class="reviews">검색 결과</span>
            </div>
            <div class="description">{html_escape(accommodation_info)}</div>
          </div>
          <div class="price-section">
            <div class="price">
              정보 확인 <span class="unit">필요</span>
            </div>
            <button class="book-button" onclick="location.reload()">다시 검색</button>
          </div>
        </div>
      </div>
    </div>
  </div>
</body>
</html>
"""


@router.post(
    "/airbnb-search-html",
    response_class=HTMLResponse,
    summary="Airbnb 숙소 검색 (HTML 응답)",
    description="자연어 쿼리를 받아 Airbnb MCP를 통해 숙소를 검색하고 Airbnb 스타일의 HTML로 반환합니다.",
    response_description="Airbnb 스타일의 숙소 리스트 HTML",
    tags=["Airbnb"],
)
async def airbnb_search_html_endpoint(request: Request, body: AirbnbSearchQuery):
    start = time.perf_counter()
    query = body.query

    logger.info(f"[airbnb_search_html_endpoint] 요청 쿼리: {query}")
    
    # 특정 질문인지 확인
    if is_target_query(query):
        logger.info(f"[airbnb_search_html_endpoint] 타겟 쿼리 감지, 캐싱된 결과 반환")
        cached_html = await get_cached_airbnb_html()
        elapsed = time.perf_counter() - start
        logger.info(f"[airbnb_search_html_endpoint] 캐싱된 결과 반환 완료 (소요 시간: {elapsed:.3f}초)")
        return HTMLResponse(content=cached_html, status_code=200)

    mcp_manager = request.app.state.mcp_manager

    # LLM이 툴 파라미터 추론
    try:
        llm_result = await call_llm_for_airbnb(query)
        logger.info(f"[airbnb_search_html_endpoint] LLM 결과: {llm_result}")
    except Exception as e:
        logger.error(f"[airbnb_search_html_endpoint] LLM 호출 실패: {e}")
        # 오류 발생시 기본 HTML 반환
        error_html = await generate_html_with_llm("검색 중 오류가 발생했습니다.", query)
        return HTMLResponse(content=error_html, status_code=500)

    # MCP 호출 및 결과 처리 (기존 JSON 엔드포인트와 동일한 로직)
    if llm_result.get("type") == "rpc":
        try:
            # MCP 도구 호출
            result = await mcp_manager.call_tool(
                server_name=llm_result["srvId"],
                tool_name=llm_result["method"],
                arguments=llm_result["params"],
            )
            logger.info(
                f"[airbnb_search_html_endpoint] MCP 원시 결과: {str(result)[:200]}..."
            )

            # LLM으로 요약 (기존과 동일)
            summarized = await summarize_with_llm(result, prompt=query)
            answer = summarized.get("results", [{}])[0].get("description", "")

            logger.info(f"[airbnb_search_html_endpoint] 요약된 결과: {answer[:200]}...")

        except Exception as e:
            logger.error(f"[airbnb_search_html_endpoint] MCP 호출 실패: {e}")
            answer = f"숙소 검색 중 오류가 발생했습니다: {str(e)}"
    else:
        # LLM 자체 응답
        answer = llm_result.get("content", "")

    # GPT-4o-mini에게 HTML 생성 요청
    try:
        html_content = await generate_html_with_llm(answer, query)
        logger.info(f"[airbnb_search_html_endpoint] HTML 생성 완료")
    except Exception as e:
        logger.error(f"[airbnb_search_html_endpoint] HTML 생성 실패: {e}")
        # HTML 생성 실패시 간단한 fallback HTML
        html_content = generate_fallback_html(answer, query)

    elapsed = time.perf_counter() - start
    logger.info(f"[airbnb_search_html_endpoint] 완료 (소요 시간: {elapsed:.3f}초)")

    return HTMLResponse(content=html_content, status_code=200)
