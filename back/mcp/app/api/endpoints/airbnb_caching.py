from fastapi import APIRouter
from fastapi.responses import HTMLResponse
import asyncio

router = APIRouter()


@router.get(
    "/airbnb/caching",
    response_class=HTMLResponse,
    summary="Airbnb 해운대 캐싱된 검색 결과",
    description="7초 후 고정된 HTML 응답을 반환합니다.",
    tags=["Airbnb"],
)
async def airbnb_caching_response():
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

    return HTMLResponse(content=html_content, status_code=200)
