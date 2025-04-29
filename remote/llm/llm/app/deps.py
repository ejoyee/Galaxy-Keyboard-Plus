# llm/app/deps.py
import os
from functools import lru_cache
from typing import AsyncGenerator

from dotenv import load_dotenv
from fastapi import HTTPException, status
from openai import AsyncOpenAI, OpenAIError

# .env 파일 로드 (애플리케이션 시작 시 한 번 호출됨)
load_dotenv()

@lru_cache # API 클라이언트 인스턴스를 캐싱하여 재사용
def get_openai_settings() -> dict:
    """OpenAI API 키와 버퍼 크기를 환경 변수에서 로드합니다."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY 환경 변수가 설정되지 않았습니다.")

    buffer_size_str = os.getenv("STREAM_BUFFER_SIZE")
    try:
        buffer_size = int(buffer_size_str)
    except ValueError:
        print(f"경고: STREAM_BUFFER_SIZE ('{buffer_size_str}')가 유효한 숫자가 아닙니다. 기본값 256을 사용합니다.")
        buffer_size = 256

    return {"api_key": api_key, "buffer_size": buffer_size}

# AsyncOpenAI 클라이언트 인스턴스 생성 (설정 로드 후)
# 참고: 클라이언트 생성 시 API 키를 직접 전달해야 합니다.
try:
    settings = get_openai_settings()
    # AsyncOpenAI 클라이언트는 애플리케이션 수명 동안 한 번 생성하여 재사용하는 것이 좋습니다.
    # 여기서는 간단하게 모듈 레벨에서 생성합니다.
    # 더 복잡한 애플리케이션에서는 FastAPI의 Lifespan 이벤트를 사용하여 관리할 수 있습니다.
    async_openai_client = AsyncOpenAI(api_key=settings["api_key"])
except ValueError as e:
    print(f"오류: OpenAI 설정 로드 실패 - {e}")
    # 애플리케이션이 API 키 없이 시작되지 않도록 처리 (예: 종료 또는 기본 클라이언트 설정)
    # 여기서는 일단 None으로 설정하고, 의존성 주입 시점에서 확인합니다.
    async_openai_client = None

def get_openai_client() -> AsyncOpenAI:
    """FastAPI 의존성 주입을 통해 AsyncOpenAI 클라이언트를 제공합니다."""
    if async_openai_client is None:
        # 이 경우는 환경 변수 로드 실패 시 발생합니다.
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="OpenAI 클라이언트가 초기화되지 않았습니다. API 키 설정을 확인하세요.",
        )
    return async_openai_client

def get_stream_buffer_size() -> int:
    """FastAPI 의존성 주입을 통해 스트림 버퍼 크기를 제공합니다."""
    # 이미 로드된 설정을 사용합니다.
    try:
        settings = get_openai_settings()
        return settings["buffer_size"]
    except ValueError:
         # 설정 로드 실패 시 기본값 반환 (또는 오류 처리)
        return 256

# OpenAI 오류를 FastAPI HTTPException으로 변환하는 헬퍼 함수
def handle_openai_error(e: OpenAIError) -> HTTPException:
    """OpenAI API 오류를 적절한 HTTP 상태 코드와 메시지로 변환합니다."""
    # OpenAI 라이브러리는 오류 유형에 따라 다른 상태 코드를 가질 수 있습니다.
    # 예: AuthenticationError -> 401, RateLimitError -> 429, NotFoundError -> 404 등
    # 여기서는 일반적인 처리를 위해 e.status_code를 사용합니다. (존재하는 경우)
    status_code = e.status_code if hasattr(e, 'status_code') and e.status_code else status.HTTP_500_INTERNAL_SERVER_ERROR
    return HTTPException(
        status_code=status_code,
        detail=str(e.message) if hasattr(e, 'message') and e.message else str(e), # 오류 메시지 포함
    )

async def generate_error_sse(e: OpenAIError) -> str:
    """OpenAI 오류 발생 시 SSE 형식의 오류 메시지를 생성합니다."""
    status_code = e.status_code if hasattr(e, 'status_code') and e.status_code else 500
    error_detail = str(e.message) if hasattr(e, 'message') and e.message else str(e)
    error_json = f'{{"error": {{ "message": "{error_detail}", "status_code": {status_code} }} }}'
    # SSE 형식: event: <event_name>\ndata: <json_string>\n\n
    return f"event: error\ndata: {error_json}\n\n"