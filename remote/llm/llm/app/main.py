# llm/app/main.py
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from openai import OpenAIError

# 라우터 임포트
from app.routers import chat, stream_buffer

# --- FastAPI 애플리케이션 생성 ---
app = FastAPI(
    title="LLM Bridge Server",
    description="Electron 클라이언트와 OpenAI API 간의 브리지 역할을 하는 FastAPI 서버입니다.",
    version="0.1.0",
)

# --- 전역 예외 핸들러 등록 ---
# OpenAI API 오류를 처리하여 일관된 JSON 응답 반환 (스트리밍 외 엔드포인트용)
@app.exception_handler(OpenAIError)
async def openai_exception_handler(request: Request, exc: OpenAIError):
    status_code = exc.status_code if hasattr(exc, 'status_code') and exc.status_code else status.HTTP_500_INTERNAL_SERVER_ERROR
    return JSONResponse(
        status_code=status_code,
        content={"detail": str(exc.message) if hasattr(exc, 'message') and exc.message else str(exc)},
    )

# --- 라우터 포함 ---
# 각 라우터 파일을 애플리케이션에 등록
app.include_router(chat.router)
app.include_router(stream_buffer.router)

# --- 루트 엔드포인트 (선택 사항) ---
@app.get("/", tags=["Root"], summary="서버 상태 확인")
async def read_root():
    """서버가 실행 중인지 확인하는 간단한 엔드포인트입니다."""
    return {"message": "LLM Bridge Server is running."}

# --- 애플리케이션 실행 (Uvicorn 사용 시) ---
# 이 블록은 'python app/main.py'로 직접 실행할 때 사용되지만,
# 보통 'uvicorn app.main:app' 명령어로 실행합니다.
if __name__ == "__main__":
    import uvicorn
    # 개발 환경에서는 --reload 옵션 사용 권장
    uvicorn.run(app, host="127.0.0.1", port=8092)