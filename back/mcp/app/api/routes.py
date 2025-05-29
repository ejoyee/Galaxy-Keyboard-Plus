from fastapi import APIRouter
from app.api.endpoints import search, geo_assist

api_router = APIRouter()

# Brave 검색 라우터만 등록
api_router.include_router(
    search.router, 
    prefix="/search",
    tags=["Search"]
)


api_router.include_router(
    geo_assist.router, 
    prefix="/geo-assist", 
    tags=["Geo Assist"]
)