from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import logging
import time

# API 라우터 import
from app.api.image_classify import router as image_classify_router
from app.api.embedding_api import router as embedding_api_router
from app.api.text_extractor_api import router as text_extractor_api_router
from app.api.image_caption_api import router as image_caption_api_router
from app.api.schedule_api import router as schedule_api_router
from app.api.save_text import router as save_text_router
from app.api.image_upload import router as image_upload_router
from app.api.search_image_info import router as search_image_info_router
from app.api.image_upload_keyword import router as image_upload_keyword_router
from app.api.qa_management import router as qa_management_router

app = FastAPI()

# CORS 설정
origins = [
    "http://localhost:3000",
    "https://k12e201.p.ssafy.io",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s - %(message)s",
)
logging.info("✅ FastAPI 애플리케이션 시작 전 로깅 설정 완료")


# 미들웨어: 요청 시간 로깅
@app.middleware("http")
async def log_request_time(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    duration = time.time() - start_time
    logging.info(
        f"⏱️ {request.method} {request.url.path} → {response.status_code} | {duration:.3f}s"
    )
    return response


# 라우터 등록
app.include_router(image_classify_router, prefix="/rag")
app.include_router(embedding_api_router, prefix="/rag")
app.include_router(text_extractor_api_router, prefix="/rag")
app.include_router(image_caption_api_router, prefix="/rag")
app.include_router(schedule_api_router, prefix="/rag")
app.include_router(save_text_router, prefix="/rag")
app.include_router(image_upload_router, prefix="/rag")
app.include_router(search_image_info_router, prefix="/rag")
app.include_router(image_upload_keyword_router, prefix="/rag")
app.include_router(qa_management_router, prefix="/rag")

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8090)
