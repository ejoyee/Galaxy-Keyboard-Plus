# llm/app/routers/chat.py
import json
from typing import List, Optional, Dict, Any, AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from openai import AsyncOpenAI, OpenAIError
from pydantic import BaseModel, Field

from app.deps import get_openai_client, handle_openai_error, generate_error_sse

# API 라우터 생성
router = APIRouter(prefix="/llm", tags=["LLM Chat"])

# --- Pydantic 모델 정의 ---
class ChatMessageInput(BaseModel):
    """OpenAI 채팅 메시지 형식"""
    role: str = Field(..., description="메시지 역할 (system, user, assistant 등)")
    content: str = Field(..., description="메시지 내용")

class ChatCompletionInput(BaseModel):
    """채팅 완료 요청의 입력 스키마"""
    messages: List[ChatMessageInput] = Field(..., description="OpenAI 채팅 메시지 목록")
    max_tokens: Optional[int] = Field(None, description="최대 생성 토큰 수 (OpenAI 기본값 사용)")
    temperature: Optional[float] = Field(None, ge=0.0, le=2.0, description="샘플링 온도 (OpenAI 기본값 사용)")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "messages": [
                        {"role": "system", "content": "You are a helpful assistant."},
                        {"role": "user", "content": "Hello, who are you?"}
                    ],
                    "max_tokens": 150,
                    "temperature": 0.7
                }
            ]
        }
    }

# --- 엔드포인트 구현 ---

@router.post(
    "/chat",
    summary="LLM 채팅 (단일 응답)",
    description="OpenAI API를 호출하여 완전한 JSON 응답을 한 번에 반환합니다.",
    response_model=Dict[str, Any] # OpenAI 응답은 동적이므로 Dict로 처리
)
async def post_chat_completion(
    payload: ChatCompletionInput,
    client: AsyncOpenAI = Depends(get_openai_client)
) -> Dict[str, Any]:
    """
    OpenAI의 chat completions API를 호출하고 전체 응답을 반환합니다.
    `stream=False` 모드로 동작합니다.
    """
    try:
        # Pydantic 모델을 dict로 변환하여 OpenAI 클라이언트에 전달
        # None 값 필드는 자동으로 제외되도록 `exclude_none=True` 사용
        request_data = payload.model_dump(exclude_none=True)

        completion = await client.chat.completions.create(
            model="gpt-4o-mini", # 대상 모델 지정
            **request_data,
            stream=False
        )
        # OpenAI 응답 객체를 dict로 변환하여 반환
        return completion.model_dump()

    except OpenAIError as e:
        # OpenAI API 오류 발생 시 처리
        raise handle_openai_error(e)
    except Exception as e:
        # 기타 예상치 못한 오류 처리
        print(f"Unexpected error in /chat: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="서버 내부 오류가 발생했습니다."
        )


async def _stream_openai_generator(payload: ChatCompletionInput, client: AsyncOpenAI) -> AsyncGenerator[str, None]:
    """OpenAI 응답 스트림을 SSE 형식으로 생성하는 비동기 제너레이터"""
    try:
        request_data = payload.model_dump(exclude_none=True)
        stream = await client.chat.completions.create(
            model="gpt-4o-mini",
            **request_data,
            stream=True
        )
        async for chunk in stream:
            # OpenAI 스트림 청크 객체를 JSON 문자열로 변환
            chunk_json = chunk.model_dump_json()
            # SSE 형식: data: <json_string>\n\n
            yield f"data: {chunk_json}\n\n"

    except OpenAIError as e:
        # 스트리밍 중 OpenAI 오류 발생 시 SSE 오류 이벤트 전송
        error_sse = await generate_error_sse(e)
        yield error_sse
    except Exception as e:
        # 기타 예상치 못한 오류 처리
        print(f"Unexpected error during streaming in /chat/stream: {e}")
        error_json = json.dumps({"error": {"message": "스트리밍 중 서버 내부 오류 발생", "status_code": 500}})
        yield f"event: error\ndata: {error_json}\n\n"


@router.post(
    "/chat/stream",
    summary="LLM 채팅 (네이티브 스트림)",
    description="OpenAI API 응답 스트림을 서버 전송 이벤트(SSE)로 직접 중계합니다."
)
async def post_chat_completion_stream(
    payload: ChatCompletionInput,
    client: AsyncOpenAI = Depends(get_openai_client)
) -> StreamingResponse:
    """
    OpenAI의 chat completions API를 `stream=True`로 호출하고,
    각 청크를 SSE 형식으로 클라이언트에 실시간 전송합니다.
    """
    return StreamingResponse(
        _stream_openai_generator(payload, client),
        media_type="text/event-stream"
    )