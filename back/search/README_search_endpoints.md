# 검색 API 엔드포인트

이 문서는 사진 검색과 정보 검색을 위한 새로운 엔드포인트를 설명합니다.

## 엔드포인트

### 1. 사진 검색 - `/search/photo`

사진 벡터에서 검색하여 관련 사진들을 반환합니다.

**요청 형식:**
```
POST /search/photo
Content-Type: application/x-www-form-urlencoded

user_id=user123&query=빨간색 인형&top_k=5
```

**응답 형식:**
```json
{
  "photos": [
    {
      "id": "photo_123",
      "text": "빨간색 인형이 침대 위에 놓여 있는 사진",
      "score": 0.95
    },
    {
      "id": "photo_456",
      "text": "빨간 드레스를 입은 인형",
      "score": 0.89
    }
  ],
  "query": "빨간색 인형",
  "expanded_queries": ["빨간색 인형", "빨간 인형", "적색 인형", "빨간색 장난감"],
  "total_time": 0.523
}
```

### 2. 정보 검색 - `/search/info`

정보 벡터에서 검색하여 관련 정보와 근거 사진을 반환합니다.

**요청 형식:**
```
POST /search/info
Content-Type: application/x-www-form-urlencoded

user_id=user123&query=에어컨 청소 방법&top_k=5&include_related_photos=true
```

**응답 형식:**
```json
{
  "info": [
    {
      "id": "info_001",
      "text": "에어컨은 정기적으로 필터를 청소하고, 실외기를 점검해야 합니다...",
      "score": 0.92,
      "related_photos": [
        {
          "id": "photo_789",
          "text": "에어컨 필터 청소하는 사진",
          "score": 0.85
        },
        {
          "id": "photo_012",
          "text": "에어컨 실외기 점검 사진",
          "score": 0.78
        }
      ]
    }
  ],
  "query": "에어컨 청소 방법",
  "expanded_queries": ["에어컨 청소 방법", "에어컨 관리", "에어컨 필터 청소"],
  "total_time": 1.234
}
```

## 특징

- **쿼리 확장**: 모든 검색에서 자동으로 쿼리를 확장하여 더 정확한 결과를 제공합니다.
- **색상/객체 분석**: 색상과 객체를 자동으로 인식하여 검색 정확도를 향상시킵니다.
- **관련 사진 연결**: 정보 검색 시 관련 사진도 함께 제공할 수 있습니다.
- **비동기 처리**: 모든 검색은 비동기로 처리되어 빠른 응답을 제공합니다.

## 사용 예시

```python
import requests

# 사진 검색
response = requests.post(
    "http://localhost:8091/search/photo",
    data={
        "user_id": "user123",
        "query": "파란색 에어컨",
        "top_k": 5
    }
)
photos = response.json()

# 정보 검색
response = requests.post(
    "http://localhost:8091/search/info",
    data={
        "user_id": "user123",
        "query": "에어컨 청소 주기",
        "top_k": 3,
        "include_related_photos": True
    }
)
info = response.json()
```
