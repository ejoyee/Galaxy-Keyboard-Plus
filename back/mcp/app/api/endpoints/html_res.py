
import asyncio

async def get_gangnam_html() -> str:
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
<div class="search-container">
    <div class="search-card">
        <h2>🏆 육미안 강남점</h2>
        <div class="rating">⭐ 5.0</div>
        <p>📍 강남구 강남대로 106길 9 1층</p>
        <div class="tags">
            <span class="tag">🅿️ 발렛파킹</span>
            <span class="tag">🥩 프리미엄 한우</span>
            <span class="tag">👥 단체석</span>
        </div>
        <a href="https://map.naver.com/v5/search/육미안 강남점" class="map-button">
            🗺️ 지도에서 보기
        </a>
    </div>

    <div class="search-card">
        <h2>💎 유니네 고깃간</h2>
        <div class="rating">⭐ 4.7</div>
        <p>📍 강남구 강남대로 98길 12 1층</p>
        <div class="tags">
            <span class="tag">🅿️ 건물주차</span>
            <span class="tag">🥩 생고기전문</span>
            <span class="tag">🌙 심야영업</span>
        </div>
        <a href="https://map.naver.com/v5/search/유니네 고깃간" class="map-button">
            🗺️ 지도에서 보기
        </a>
    </div>

    <div class="search-card">
        <h2>👑 다몽집 신논현본점</h2>
        <div class="rating">⭐ 4.8</div>
        <p>📍 강남구 강남대로 100길 13 2층</p>
        <div class="tags">
            <span class="tag">🅿️ 발렛파킹</span>
            <span class="tag">🥩 무한리필</span>
            <span class="tag">💳 카드가능</span>
        </div>
        <a href="https://map.naver.com/v5/search/다몽집 신논현본점" class="map-button">
            🗺️ 지도에서 보기
        </a>
    </div>
</div>

<style>
.search-container {
    padding: 16px;
    background: linear-gradient(135deg, #E8F8F5 0%, #E1F5FE 50%, #F3E5F5 100%);
    min-height: 100vh;
}

.search-card {
    background: rgba(255,255,255,0.9);
    border-radius: 20px;
    padding: 20px;
    margin-bottom: 16px;
    box-shadow: 0 4px 20px rgba(0,0,0,0.08);
    border: 1px solid rgba(255,255,255,0.6);
    backdrop-filter: blur(20px) saturate(120%);
}

.search-card h2 {
    color: #1565C0;
    font-size: 20px;
    font-weight: bold;
    margin: 0 0 8px 0;
}

.rating {
    color: #546E7A;
    font-size: 16px;
    margin-bottom: 8px;
}

.tags {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    margin: 12px 0;
}

.tag {
    background: linear-gradient(45deg, #26C6DA, #4FC3F7, #81D4FA);
    color: white;
    padding: 6px 12px;
    border-radius: 20px;
    font-size: 14px;
}

.map-button {
    display: block;
    background: linear-gradient(135deg, #1565C0 0%, #42A5F5 100%);
    color: white;
    text-align: center;
    padding: 16px;
    border-radius: 28px;
    text-decoration: none;
    font-weight: bold;
    margin-top: 16px;
    box-shadow: 0 4px 12px rgba(21,101,192,0.3);
}

@media (max-width: 428px) {
    .search-container {
        padding: 12px;
    }
    
    .search-card {
        padding: 16px;
    }
}
</style></body></html>
    """

    return html_content