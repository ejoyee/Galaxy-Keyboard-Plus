from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    """웹 검색 요청 모델"""

    query: str = Field(..., description="검색 쿼리")

    class Config:
        schema_extra = {"example": {"query": "인공지능 기술"}}


class SearchResponse(BaseModel):
    answer: str = Field(..., description="최종 답변")
class Location(BaseModel):
    latitude: float
    longitude: float

# ── 위치 기반 요청/응답 ───────────────────────────
class LocalSearchRequest(BaseModel):
    query: str
    location: Location

class LocalSearchResponse(BaseModel):
    answer: str

