# app/models/qa_models.py

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class QAStoreRequest(BaseModel):
    """질문-답변 저장 요청 모델"""
    question: str = Field(..., description="질문 내용", min_length=1, max_length=1000)
    answer: str = Field(..., description="답변 내용", min_length=1, max_length=5000)
    
    class Config:
        json_schema_extra = {
            "example": {
                "question": "FastAPI에서 비동기 처리는 어떻게 구현하나요?",
                "answer": "FastAPI에서는 async/await 키워드를 사용하여 비동기 처리를 구현할 수 있습니다. 예를 들어: async def get_data(): return await database.fetch_all()"
            }
        }


class QAStoreResponse(BaseModel):
    """질문-답변 저장 응답 모델"""
    success: bool = Field(..., description="저장 성공 여부")
    qa_id: str = Field(..., description="생성된 QA ID")
    message: str = Field(..., description="결과 메시지")
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "qa_id": "qa_20250530_001",
                "message": "질문-답변이 성공적으로 저장되었습니다."
            }
        }


class QAQueryRequest(BaseModel):
    """질문 조회 요청 모델"""
    question: str = Field(..., description="검색할 질문", min_length=1, max_length=1000)
    
    class Config:
        json_schema_extra = {
            "example": {
                "question": "FastAPI 비동기 처리 방법이 궁금합니다"
            }
        }


class QAResult(BaseModel):
    """개별 QA 결과 모델"""
    qa_id: str = Field(..., description="QA ID")
    question: str = Field(..., description="질문")
    answer: str = Field(..., description="답변")
    similarity_score: float = Field(..., description="유사도 점수")
    created_at: Optional[str] = Field(None, description="생성일시")


class QAQueryResponse(BaseModel):
    """질문 조회 응답 모델"""
    success: bool = Field(..., description="조회 성공 여부")
    total_found: int = Field(..., description="찾은 결과 총 개수")
    results: List[QAResult] = Field(..., description="검색 결과 목록")
    message: str = Field(..., description="결과 메시지")
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "total_found": 2,
                "results": [
                    {
                        "qa_id": "qa_20250530_001",
                        "question": "FastAPI에서 비동기 처리는 어떻게 구현하나요?",
                        "answer": "FastAPI에서는 async/await 키워드를 사용하여 비동기 처리를 구현할 수 있습니다.",
                        "similarity_score": 0.95,
                        "created_at": "2025-05-30T10:30:00"
                    }
                ],
                "message": "2개의 관련 답변을 찾았습니다."
            }
        }


class QAListResponse(BaseModel):
    """QA 목록 조회 응답 모델"""
    success: bool = Field(..., description="조회 성공 여부")
    total_count: int = Field(..., description="총 QA 개수")
    results: List[QAResult] = Field(..., description="QA 목록")
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "total_count": 10,
                "results": []
            }
        }


class QADeleteResponse(BaseModel):
    """QA 삭제 응답 모델"""
    success: bool = Field(..., description="삭제 성공 여부")
    message: str = Field(..., description="결과 메시지")
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "QA가 성공적으로 삭제되었습니다."
            }
        }
