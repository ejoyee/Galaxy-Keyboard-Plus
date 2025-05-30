# app/api/qa_management.py

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
import os
import uuid
from datetime import datetime
from typing import List, Optional
from dotenv import load_dotenv
from pinecone import Pinecone
from openai import OpenAI
import json
import logging

from app.models.qa_models import (
    QAStoreRequest, QAStoreResponse, 
    QAQueryRequest, QAQueryResponse, QAResult,
    QAListResponse, QADeleteResponse
)

load_dotenv()

router = APIRouter(tags=["QA Management"])

# 환경 변수 설정
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_INDEX_NAME = os.getenv("PINECONE_INDEX_NAME")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# QA 전용 네임스페이스
QA_NAMESPACE = "qa_system"

# 클라이언트 초기화
openai_client = OpenAI(api_key=OPENAI_API_KEY)

def get_pinecone_index():
    """Pinecone 인덱스 연결"""
    try:
        pc = Pinecone(api_key=PINECONE_API_KEY)
        return pc.Index(PINECONE_INDEX_NAME)
    except Exception as e:
        logging.error(f"Pinecone 연결 실패: {str(e)}")
        raise HTTPException(status_code=500, detail="데이터베이스 연결에 실패했습니다.")

def generate_embedding(text: str) -> List[float]:
    """OpenAI API를 사용하여 텍스트 임베딩 생성"""
    try:
        response = openai_client.embeddings.create(
            model="text-embedding-3-small",
            input=text,
            encoding_format="float"
        )
        return response.data[0].embedding
    except Exception as e:
        logging.error(f"임베딩 생성 실패: {str(e)}")
        raise HTTPException(status_code=500, detail="임베딩 생성에 실패했습니다.")

def generate_qa_id() -> str:
    """고유한 QA ID 생성"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    unique_id = str(uuid.uuid4())[:8]
    return f"qa_{timestamp}_{unique_id}"

@router.post("/qa/store", response_model=QAStoreResponse)
async def store_qa(request: QAStoreRequest):
    """
    새로운 질문-답변을 저장합니다.
    
    - **question**: 질문 내용 (1-1000자)
    - **answer**: 답변 내용 (1-5000자)
    """
    try:
        # QA ID 생성
        qa_id = generate_qa_id()
        
        # 질문 위주로 임베딩 생성 (답변도 포함하지만 질문에 가중치 부여)
        question_weighted = f"질문: {request.question} {request.question}"  # 질문을 두 번 반복하여 가중치 부여
        combined_text = f"{question_weighted}\n답변: {request.answer}"
        embedding = generate_embedding(combined_text)
        
        # 메타데이터 준비
        metadata = {
            "qa_id": qa_id,
            "question": request.question,
            "answer": request.answer,
            "created_at": datetime.now().isoformat(),
            "type": "qa_pair"
        }
        
        # Pinecone에 저장
        index = get_pinecone_index()
        index.upsert(
            vectors=[(qa_id, embedding, metadata)],
            namespace=QA_NAMESPACE
        )
        
        logging.info(f"QA 저장 완료: {qa_id}")
        
        return QAStoreResponse(
            success=True,
            qa_id=qa_id,
            message="질문-답변이 성공적으로 저장되었습니다."
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"QA 저장 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=f"저장 중 오류가 발생했습니다: {str(e)}")

@router.post("/qa/query", response_model=QAQueryResponse)
async def query_qa(request: QAQueryRequest):
    """
    질문에 대한 유사한 답변을 검색합니다.
    
    - **question**: 검색할 질문 (1-1000자)
    """
    try:
        # 질문 임베딩 생성 (질문에 가중치 부여)
        search_text = f"질문: {request.question} {request.question}"  # 저장된 데이터와 동일한 패턴
        question_embedding = generate_embedding(search_text)
        
        # 검색 조건 설정 (개선된 값)
        filter_conditions = {"type": "qa_pair"}
        top_k = 10  # 더 많은 결과 검색
        
        # Pinecone에서 검색
        index = get_pinecone_index()
        search_results = index.query(
            vector=question_embedding,
            top_k=top_k,
            include_metadata=True,
            filter=filter_conditions,
            namespace=QA_NAMESPACE
        )
        
        # 디버깅 정보 로깅
        logging.info(f"QA 검색 요청: '{request.question}'")
        logging.info(f"검색 결과 개수: {len(search_results.matches)}")
        if search_results.matches:
            top_scores = [round(match.score, 4) for match in search_results.matches[:5]]
            logging.info(f"상위 5개 유사도 점수: {top_scores}")
        
        # 결과 처리 - 다양한 유사도 수준을 고려
        high_quality_results = []  # 0.7 이상
        medium_quality_results = []  # 0.5-0.7
        low_quality_results = []  # 0.3-0.5
        very_low_quality_results = []  # 0.1-0.3
        
        for match in search_results.matches:
            metadata = match.metadata
            result = QAResult(
                qa_id=metadata["qa_id"],
                question=metadata["question"],
                answer=metadata["answer"],
                similarity_score=round(match.score, 4),
                created_at=metadata.get("created_at")
            )
            
            if match.score >= 0.7:
                high_quality_results.append(result)
            elif match.score >= 0.5:
                medium_quality_results.append(result)
            elif match.score >= 0.3:
                low_quality_results.append(result)
            elif match.score >= 0.1:
                very_low_quality_results.append(result)
        
        # 결과 선택 로직 - 더 관대한 기준
        results = []
        quality_message = ""
        
        if high_quality_results:
            results = high_quality_results[:3]  # 고품질 결과 최대 3개
            quality_message = " (높은 유사도)"
        elif medium_quality_results:
            results = medium_quality_results[:3]  # 중품질 결과 최대 3개
            quality_message = " (중간 유사도)"
        elif low_quality_results:
            results = low_quality_results[:2]  # 저품질 결과 최대 2개
            quality_message = " (낮은 유사도)"
        elif very_low_quality_results:
            results = very_low_quality_results[:1]  # 매우 낮은 품질 결과 1개
            quality_message = " (매우 낮은 유사도 - 참고용)"
        
        # 메시지 생성
        if results:
            message = f"{len(results)}개의 관련 답변을 찾았습니다{quality_message}"
        else:
            message = "관련된 답변을 찾지 못했습니다."
        
        # 결과 로깅
        logging.info(f"반환되는 결과 개수: {len(results)}")
        if results:
            logging.info(f"최고 유사도: {results[0].similarity_score}")
        
        return QAQueryResponse(
            success=True,
            total_found=len(results),
            results=results,
            message=message
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"QA 검색 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=f"검색 중 오류가 발생했습니다: {str(e)}")

@router.get("/qa/list", response_model=QAListResponse)
async def list_qa(
    offset: int = 0,
    limit: int = 50
):
    """
    저장된 QA 목록을 조회합니다.
    
    - **offset**: 시작 위치 (기본값: 0)
    - **limit**: 조회할 개수 (기본값: 50, 최대: 100)
    """
    try:
        if limit > 100:
            limit = 100
            
        # 검색 조건 설정
        filter_conditions = {"type": "qa_pair"}
        
        # Pinecone에서 모든 QA 조회 (더미 벡터로 검색)
        index = get_pinecone_index()
        
        # 빈 벡터로 모든 항목 검색 (임시 방법)
        # 실제로는 별도의 QA 목록 관리 시스템이 필요할 수 있습니다.
        dummy_embedding = [0.0] * 1536  # OpenAI embedding 차원
        
        search_results = index.query(
            vector=dummy_embedding,
            top_k=min(1000, offset + limit),  # 충분히 큰 수로 검색
            include_metadata=True,
            filter=filter_conditions,
            namespace=QA_NAMESPACE
        )
        
        # 결과 처리 및 페이지네이션
        all_results = []
        for match in search_results.matches:
            metadata = match.metadata
                
            result = QAResult(
                qa_id=metadata["qa_id"],
                question=metadata["question"],
                answer=metadata["answer"],
                similarity_score=0.0,  # 목록 조회에서는 유사도 의미 없음
                created_at=metadata.get("created_at")
            )
            all_results.append(result)
        
        # 생성일시 기준 정렬 (최신순)
        all_results.sort(key=lambda x: x.created_at or "", reverse=True)
        
        # 페이지네이션 적용
        paginated_results = all_results[offset:offset + limit]
        
        return QAListResponse(
            success=True,
            total_count=len(all_results),
            results=paginated_results
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"QA 목록 조회 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=f"목록 조회 중 오류가 발생했습니다: {str(e)}")

@router.delete("/qa/{qa_id}", response_model=QADeleteResponse)
async def delete_qa(qa_id: str):
    """
    특정 QA를 삭제합니다.
    
    - **qa_id**: 삭제할 QA의 ID
    """
    try:
        # Pinecone에서 해당 ID 존재 여부 확인
        index = get_pinecone_index()
        
        # 먼저 해당 QA가 존재하는지 확인
        fetch_result = index.fetch(ids=[qa_id], namespace=QA_NAMESPACE)
        
        if qa_id not in fetch_result.vectors:
            raise HTTPException(status_code=404, detail="해당 QA를 찾을 수 없습니다.")
        
        # Pinecone에서 삭제
        index.delete(ids=[qa_id], namespace=QA_NAMESPACE)
        
        logging.info(f"QA 삭제 완료: {qa_id}")
        
        return QADeleteResponse(
            success=True,
            message="QA가 성공적으로 삭제되었습니다."
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"QA 삭제 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=f"삭제 중 오류가 발생했습니다: {str(e)}")

@router.get("/qa/stats")
async def get_qa_stats():
    """
    QA 시스템 통계 정보를 조회합니다.
    """
    try:
        index = get_pinecone_index()
        
        # 네임스페이스 통계 조회
        stats = index.describe_index_stats(filter={"type": "qa_pair"})
        
        qa_count = 0
        if QA_NAMESPACE in stats.namespaces:
            qa_count = stats.namespaces[QA_NAMESPACE].vector_count
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "total_qa_count": qa_count,
                "namespace": QA_NAMESPACE,
                "index_name": PINECONE_INDEX_NAME
            }
        )
        
    except Exception as e:
        logging.error(f"QA 통계 조회 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=f"통계 조회 중 오류가 발생했습니다: {str(e)}")
