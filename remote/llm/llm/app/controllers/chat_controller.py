# llm/app/controllers/chat_controller.py
from typing import Dict, Any

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from openai import AsyncOpenAI, OpenAIError

# 의존성, 모델, 서비스 임포트
from app.core.openai_client import get_openai_client, handle_openai_error
from app.core.config import get_stream_buffer_size
from app.models.chat import ChatCompletionInput, ChatSimpleResponse
from app.services.chat_service import ChatService

# 컨트롤러 라우터 생성
router = APIRouter(prefix="/llm", tags=["LLM Chat"])

@router.post(
    "/chat",
    summary="LLM 채팅 (단순 텍스트 응답)",
    description="OpenAI API를 호출하여 응답 메시지의 내용(content)만 추출하여 반환합니다.",
    response_model=ChatSimpleResponse
)
async def post_chat_completion(
    payload: ChatCompletionInput,
    client: AsyncOpenAI = Depends(get_openai_client),
    # ChatService를 직접 주입할 수도 있지만, 여기서는 static method를 사용
) -> ChatSimpleResponse:
    """컨트롤러: 요청을 받아 ChatService.create_completion 호출 후 결과를 파싱하여 단순 텍스트 응답 반환"""
    try:
        # 서비스 계층 호출 (기존과 동일, 전체 OpenAI 응답 객체를 받음)
        full_result = await ChatService.create_completion(payload, client)

        # 결과 파싱: choices[0].message.content 추출
        # 안전하게 접근하기 위해 get 메서드와 기본값 사용 또는 명시적 확인
        if (choices := full_result.get("choices")) and isinstance(choices, list) and len(choices) > 0:
            first_choice = choices[0]
            if (message := first_choice.get("message")) and isinstance(message, dict):
                if (content := message.get("content")) is not None:
                    # 성공적으로 content 추출
                    return ChatSimpleResponse(response=content)

        # 정상 응답 받았으나 예상 구조가 아닌 경우 (예: content가 null 또는 없는 경우)
        print(f"경고: OpenAI 응답에서 'choices[0].message.content'를 추출하지 못했습니다. Full response: {full_result}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="LLM 응답을 처리하는 중 오류가 발생했습니다. (응답 구조 불일치)"
        )
    except OpenAIError as e:
        # 서비스에서 발생한 OpenAI 오류를 HTTP 예외로 변환하여 클라이언트에 반환
        raise handle_openai_error(e)
    except HTTPException:
         # 위에서 발생시킨 HTTPException은 그대로 전달
        raise
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