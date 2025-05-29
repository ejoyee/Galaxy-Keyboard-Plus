from fastapi import APIRouter
from app.api.endpoints import search
from app.api.endpoints import airbnb

api_router = APIRouter()

# Brave 검색 라우터만 등록
api_router.include_router(search.router, prefix="/search", tags=["Search"])
api_router.include_router(airbnb.router, prefix="/search", tags=["Search"])
