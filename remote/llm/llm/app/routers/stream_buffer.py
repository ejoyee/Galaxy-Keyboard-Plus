# llm/app/routers/stream_buffer.py
import json
from typing import AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from openai import AsyncOpenAI, OpenAIError

from app.deps import get_openai_client, get_stream_buffer_size, generate_error_sse
from app.routers.chat import ChatCompletionInput # 입력 스키마 재사용

# API 라우터 생성
router = APIRouter(prefix="/llm", tags=["LLM Chat"])

async def _buffered_stream_generator(
    payload: ChatCompletionInput,
    client: AsyncOpenAI,
    buffer_size: int
) -> AsyncGenerator[str, None]:
    """OpenAI 응답 스트림을 버퍼링하여 SSE 형식으로 생성하는 비동기 제너레이터"""
    buffer = bytearray() # 바이트 데이터를 담을 버퍼

    try:
        request_data = payload.model_dump(exclude_none=True)
        stream = await client.chat.completions.create(
            model="gpt-4o-mini",
            **request_data,
            stream=True
        )

        async for chunk in stream:
            # 스트림에서 실제 텍스트 콘텐츠 추출 (있는 경우)
            content = chunk.choices[0].delta.content
            if content:
                # 텍스트를 UTF-8 바이트로 인코딩하여 버퍼에 추가
                buffer.extend(content.encode('utf-8'))

                # 버퍼 크기가 설정된 임계값을 넘으면 청크 전송
                while len(buffer) >= buffer_size:
                    # 버퍼에서 지정된 크기만큼 잘라내어 전송할 청크 생성
                    chunk_to_send = buffer[:buffer_size]
                    # 남은 데이터를 버퍼에 유지
                    buffer = buffer[buffer_size:]

                    # 바이트 데이터를 다시 UTF-8 문자열로 디코딩하여 SSE 형식으로 yield
                    # 만약 디코딩 오류가 발생할 수 있다면, 오류 처리 로직 추가 필요
                    # (예: try-except block, 혹은 errors='replace'/'ignore' 사용)
                    try:
                        yield f"data: {chunk_to_send.decode('utf-8')}\n\n"
                    except UnicodeDecodeError:
                         # 부분적인 멀티바이트 문자가 잘렸을 경우 발생 가능
                         # 여기서는 간단히 무시하거나 대체 문자로 처리할 수 있음
                         # 혹은 버퍼 로직을 수정하여 문자 경계에서 자르도록 개선 필요
                         yield f"data: {chunk_to_send.decode('utf-8', errors='replace')}\n\n"


        # 스트림 종료 후 버퍼에 남은 데이터 전송
        if buffer:
            try:
                yield f"data: {buffer.decode('utf-8')}\n\n"
            except UnicodeDecodeError:
                yield f"data: {buffer.decode('utf-8', errors='replace')}\n\n"

    except OpenAIError as e:
        # 스트리밍 중 OpenAI 오류 발생 시 SSE 오류 이벤트 전송
        error_sse = await generate_error_sse(e)
        yield error_sse
    except Exception as e:
        # 기타 예상치 못한 오류 처리
        print(f"Unexpected error during streaming in /chat/stream-buffer: {e}")
        error_json = json.dumps({"error": {"message": "버퍼 스트리밍 중 서버 내부 오류 발생", "status_code": 500}})
        yield f"event: error\ndata: {error_json}\n\n"


@router.post(
    "/chat/stream-buffer",
    summary="LLM 채팅 (버퍼링된 스트림)",
    description="OpenAI 응답 스트림을 내부 버퍼에 누적하고, 일정 크기마다 청크로 나누어 SSE로 전송합니다."
)
async def post_chat_completion_stream_buffer(
    payload: ChatCompletionInput, # chat.py의 모델 재사용
    client: AsyncOpenAI = Depends(get_openai_client),
    buffer_size: int = Depends(get_stream_buffer_size) # .env 또는 기본값(256) 사용
) -> StreamingResponse:
    """
    OpenAI의 chat completions API를 `stream=True`로 호출하고,
    응답 토큰을 버퍼에 모아 일정 크기(기본 256바이트)가 되면
    SSE 형식(`data: <텍스트 청크>\n\n`)으로 클라이언트에 전송합니다.
    """
    if buffer_size <= 0:
        raise HTTPException(status_code=400, detail="Buffer size must be positive.")

    return StreamingResponse(
        _buffered_stream_generator(payload, client, buffer_size),
        media_type="text/event-stream"
    )