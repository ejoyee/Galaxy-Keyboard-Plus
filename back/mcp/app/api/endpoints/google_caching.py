from fastapi import APIRouter
from fastapi.responses import HTMLResponse
import asyncio

router = APIRouter()


@router.get(
    "/google/caching",
    response_class=HTMLResponse,
    summary="Google 해운대 캐싱된 검색 결과",
    description="7초 후 고정된 HTML 응답을 반환합니다.",
    tags=["Google"],
)
async def google_caching_response():
    await asyncio.sleep(7)  # 7초 대기

    html_content = """
<html>
<head>
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <style>
        body {
            margin: 0;
            padding: 16px;
            background: linear-gradient(135deg, #E8F8F5 0%, #E1F5FE 50%, #F3E5F5 100%);
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            min-height: 100vh;
        }

        .container {
            max-width: 100vw;
            margin: 0 auto;
            padding-top: env(safe-area-inset-top);
            padding-bottom: env(safe-area-inset-bottom);
        }

        .card {
            background: rgba(255,255,255,0.9);
            border: 1px solid rgba(255,255,255,0.6);
            border-radius: 20px;
            padding: 20px;
            margin-bottom: 12px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.08);
            backdrop-filter: blur(20px) saturate(120%);
            transform: translateZ(0);
            transition: transform 200ms ease;
        }

        .card:active {
            transform: scale(0.97);
        }

        .place-name {
            font-size: 20px;
            font-weight: bold;
            color: #1565C0;
            margin-bottom: 8px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .rating {
            color: #546E7A;
            font-size: 14px;
        }

        .address {
            color: #546E7A;
            font-size: 16px;
            line-height: 1.5;
            margin-bottom: 12px;
        }

        .map-button {
            background: linear-gradient(135deg, #1565C0 0%, #42A5F5 100%);
            color: white;
            border: none;
            border-radius: 28px;
            padding: 16px;
            width: 100%;
            font-size: 18px;
            font-weight: bold;
            margin-top: 12px;
            height: 56px;
            box-shadow: 0 4px 12px rgba(21,101,192,0.3);
            display: flex;
            align-items: center;
            justify-content: center;
            text-decoration: none;
        }

        .map-button:active {
            transform: scale(0.98);
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="card">
            <div class="place-name">
                해운대해수욕장
                <span class="rating">⭐ 4.5</span>
            </div>
            <div class="address">부산 해운대구 우동</div>
            <a href="https://map.naver.com/v5/search/해운대해수욕장" class="map-button">
                🗺️ 지도에서 보기
            </a>
        </div>

        <div class="card">
            <div class="place-name">
                달맞이길
                <span class="rating">⭐ 4.6</span>
            </div>
            <div class="address">부산 해운대구 중동</div>
            <a href="https://map.naver.com/v5/search/달맞이길" class="map-button">
                🗺️ 지도에서 보기
            </a>
        </div>

        <div class="card">
            <div class="place-name">
                청사포
                <span class="rating">⭐ 4.4</span>
            </div>
            <div class="address">부산 해운대구 중동</div>
            <a href="https://map.naver.com/v5/search/청사포" class="map-button">
                🗺️ 지도에서 보기
            </a>
        </div>

        <div class="card">
            <div class="place-name">
                해운대 블루라인파크
                <span class="rating">⭐ 4.4</span>
            </div>
            <div class="address">부산 해운대구 청사포로 116</div>
            <a href="https://map.naver.com/v5/search/해운대블루라인파크" class="map-button">
                🗺️ 지도에서 보기
            </a>
        </div>

        <div class="card">
            <div class="place-name">
                BUSAN X the SKY
                <span class="rating">⭐ 4.5</span>
            </div>
            <div class="address">부산 해운대구 달맞이길 30</div>
            <a href="https://map.naver.com/v5/search/BUSAN X the SKY" class="map-button">
                🗺️ 지도에서 보기
            </a>
        </div>
    </div>
</body>
</html>
    """

    return HTMLResponse(content=html_content, status_code=200)
