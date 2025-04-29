# llm/app/controllers/chat_controller.py
from typing import Dict, Any

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from openai import AsyncOpenAI, OpenAIError

# 의존성, 모델, 서비스 임포트
from app.core.openai_client import get_openai_client, handle_openai_error
from app.core.config import get_stream_buffer_size
from app.models.chat import ChatCompletionInput
from app.services.chat_service import ChatService

# 컨트롤러 라우터 생성
router = APIRouter(prefix="/llm", tags=["LLM Chat"])

@router.post(
    "/chat",
    summary="LLM 채팅 (단일 응답)",
    description="OpenAI API를 호출하여 완전한 JSON 응답을 한 번에 반환합니다.",
    response_model=Dict[str, Any] # 동적 OpenAI 응답 처리
)
async def post_chat_completion(
    payload: ChatCompletionInput,
    client: AsyncOpenAI = Depends(get_openai_client),
    # ChatService를 직접 주입할 수도 있지만, 여기서는 static method를 사용
) -> Dict[str, Any]:
    """컨트롤러: 요청을 받아 ChatService.create_completion 호출 후 응답 반환"""
    try:
        result = await ChatService.create_completion(payload, client)
        return result
    except OpenAIError as e:
        # 서비스에서 발생한 OpenAI 오류를 HTTP 예외로 변환하여 클라이언트에 반환
        raise handle_openai_error(e)
    except Exception as e:
        # 기타 예상치 못한 오류 처리
        print(f"Unexpected error in /chat controller: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="서버 내부 오류가 발생했습니다.",
        )

@router.post(
    "/chat/stream",
    summary="LLM 채팅 (네이티브 스트림)",
    description="OpenAI API 응답 스트림을 SSE로 직접 중계합니다."
)
async def post_chat_completion_stream(
    payload: ChatCompletionInput,
    client: AsyncOpenAI = Depends(get_openai_client)
    # ChatService 주입 가능
) -> StreamingResponse:
    """컨트롤러: 요청을 받아 ChatService.stream_completion 제너레이터를 StreamingResponse로 반환"""
    # 서비스의 제너레이터를 직접 StreamingResponse에 전달
    return StreamingResponse(
        ChatService.stream_completion(payload, client),
        media_type="text/event-stream"
    )

@router.post(
    "/chat/stream-buffer",
    summary="LLM 채팅 (버퍼링된 스트림)",
    description="OpenAI 응답 스트림을 버퍼링하여 SSE 청크로 전송합니다."
)
async def post_chat_completion_stream_buffer(
    payload: ChatCompletionInput,
    client: AsyncOpenAI = Depends(get_openai_client),
    buffer_size: int = Depends(get_stream_buffer_size)
    # ChatService 주입 가능
) -> StreamingResponse:
    """컨트롤러: 요청을 받아 ChatService.stream_buffered_completion 제너레이터를 StreamingResponse로 반환"""
    if buffer_size <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Buffer size must be positive.")

    # 서비스의 버퍼링 제너레이터를 StreamingResponse에 전달
    return StreamingResponse(
        ChatService.stream_buffered_completion(payload, client, buffer_size),
        media_type="text/event-stream"
    )