# llm/app/main.py
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from openai import OpenAIError

# 컨트롤러 라우터 및 전역 예외 핸들러 헬퍼 임포트
from app.controllers import chat_controller
from app.core.openai_client import handle_openai_error # 전역 핸들러에서 사용

# FastAPI 애플리케이션 생성
app = FastAPI(
    title="LLM Bridge Server (Refactored)",
    description="Electron 클라이언트와 OpenAI API 간의 브리지 역할을 하는 FastAPI 서버 (MVC 스타일 구조).",
    version="0.2.0",
)

# --- 전역 예외 핸들러 등록 ---
# 서비스 계층에서 처리되지 않고 컨트롤러까지 전파된 OpenAIError 처리
# (주로 비-스트리밍 엔드포인트에서 발생)
@app.exception_handler(OpenAIError)
async def openai_exception_handler(request: Request, exc: OpenAIError):
    # handle_openai_error가 HTTPException 객체를 반환하므로,
    # 해당 객체의 status_code와 detail을 사용하여 JSONResponse 생성
    http_exception = handle_openai_error(exc)
    return JSONResponse(
        status_code=http_exception.status_code,
        content={"detail": http_exception.detail},
    )

# --- 컨트롤러 라우터 포함 ---
app.include_router(chat_controller.router)

# --- 루트 엔드포인트 ---
@app.get("/", tags=["Root"], summary="서버 상태 확인")
async def read_root():
    """서버가 실행 중인지 확인하는 간단한 엔드포인트입니다."""
    return {"message": "LLM Bridge Server is running (Refactored)."}

# --- 애플리케이션 실행 (Uvicorn 사용 시) ---
if __name__ == "__main__":
    import uvicorn
    # 설정 로드 시도 (환경 변수 누락 시 여기서 오류 발생 가능)
    try:
        from app.core.config import get_settings
        get_settings() # 시작 시 설정 유효성 검사
        print("Application settings loaded successfully.")
    except ValueError as e:
        print(f"CRITICAL ERROR: Failed to load application settings. Server cannot start.")
        print(f"Error details: {e}")
        exit(1) # 설정 로드 실패 시 서버 시작 중단

    uvicorn.run(app, host="127.0.0.1", port=8092)