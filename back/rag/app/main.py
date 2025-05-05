## RAG 관련 진입점
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from app.api.pinecone_test import router as pinecone_test_router
import logging

app = FastAPI()

# 로깅 기본 설정
logging.basicConfig(
    level=logging.DEBUG,  # 로그 레벨: DEBUG, INFO, WARNING, ERROR, CRITICAL
    format="[%(asctime)s] %(levelname)s - %(message)s",
)

# 로그 출력 테스트
logging.info("✅ FastAPI 애플리케이션 시작 전 로깅 설정 완료")

# API 라우터 등록
app.include_router(pinecone_test_router, prefix="/rag")

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=9000)
