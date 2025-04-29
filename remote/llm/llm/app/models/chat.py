# llm/app/models/chat.py
from typing import List, Optional
from pydantic import BaseModel, Field

class ChatMessageInput(BaseModel):
    """OpenAI 채팅 메시지 형식"""
    role: str = Field(..., description="메시지 역할 (system, user, assistant 등)")
    content: str = Field(..., description="메시지 내용")

class ChatCompletionInput(BaseModel):
    """채팅 완료 요청의 입력 스키마"""
    messages: List[ChatMessageInput] = Field(..., description="OpenAI 채팅 메시지 목록")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "messages": [
                        {"role": "system", "content": "You are a helpful assistant."},
                        {"role": "user", "content": "안녕? 니 소개를 해줘"}
                    ]
                }
            ]
        }
    }

class ChatSimpleResponse(BaseModel):
    """단순 텍스트 응답을 위한 스키마"""
    response: str = Field(..., description="LLM이 생성한 응답 텍스트")
