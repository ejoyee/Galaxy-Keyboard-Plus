from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
import os
import uuid
from datetime import datetime
from typing import List, Dict
from dotenv import load_dotenv
from pinecone import Pinecone
from openai import OpenAI
import logging
import re

from app.models.qa_models import (
    QAStoreRequest,
    QAStoreResponse,
    QAQueryRequest,
    QAQueryResponse,
    QAResult,
    QAListResponse,
    QADeleteResponse,
)

load_dotenv()

router = APIRouter(tags=["QA Management"])

PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_INDEX_NAME = os.getenv("PINECONE_INDEX_NAME")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
QA_NAMESPACE = "qa_system"

openai_client = OpenAI(api_key=OPENAI_API_KEY)

# 개선된 설정값들
MIN_SIMILARITY_THRESHOLD = 0.3  # 더 관대한 임계값
MAX_CONTEXT_RESULTS = 8  # 더 많은 컨텍스트 활용


def get_pinecone_index():
    try:
        pc = Pinecone(api_key=PINECONE_API_KEY)
        return pc.Index(PINECONE_INDEX_NAME)
    except Exception as e:
        logging.error(f"Pinecone 연결 실패: {str(e)}")
        raise HTTPException(status_code=500, detail="데이터베이스 연결에 실패했습니다.")


def generate_embedding(text: str) -> List[float]:
    try:
        response = openai_client.embeddings.create(
            model="text-embedding-3-small", input=text, encoding_format="float"
        )
        return response.data[0].embedding
    except Exception as e:
        logging.error(f"임베딩 생성 실패: {str(e)}")
        raise HTTPException(status_code=500, detail="임베딩 생성에 실패했습니다.")


def extract_keywords(text: str) -> List[str]:
    """질문에서 핵심 키워드 추출"""
    stopwords = {'은', '는', '이', '가', '을', '를', '에', '에서', '로', '으로', '와', '과', '도', '만', '부터', '까지', '의', '에게', '께', '한테'}
    words = re.findall(r'[가-힣a-zA-Z0-9]+', text)
    keywords = [word for word in words if word not in stopwords and len(word) > 1]
    return keywords


def filter_relevant_results(question: str, search_results: List[QAResult]) -> List[QAResult]:
    """관련성 있는 결과만 필터링"""
    if not search_results:
        return []
    
    question_keywords = set(extract_keywords(question))
    filtered_results = []
    
    for result in search_results:
        # 유사도 기본 필터링
        if result.similarity_score >= MIN_SIMILARITY_THRESHOLD:
            filtered_results.append(result)
            continue
            
        # 키워드 매칭으로 추가 검증
        result_keywords = set(extract_keywords(result.question + " " + result.answer))
        if question_keywords.intersection(result_keywords):
            filtered_results.append(result)
    
    return filtered_results[:MAX_CONTEXT_RESULTS]


def generate_rag_response(user_question: str, search_results: List[QAResult]) -> str:
    try:
        # 관련성 있는 결과 필터링
        relevant_results = filter_relevant_results(user_question, search_results)
        
        if not relevant_results:
            return "해당 질문에 대한 구체적인 정보가 준비되어 있지 않습니다. 다른 질문이 있으시면 답변드리겠습니다."
        
        # 컨텍스트 구성
        context_info = "\n".join(
            f"참고자료 {i+1}:\n질문: {r.question}\n내용: {r.answer}\n"
            for i, r in enumerate(relevant_results)
        )
        
        prompt = f"""
당신은 삼성 청년 소프트웨어 아카데미 프로젝트 발표 Q&A를 담당합니다.
아래 참고자료의 내용을 바탕으로 질문에 답변하세요.

[중요 규칙]
1. 참고자료에 있는 내용만 사용하세요
2. 간결하고 직접적으로 답변하세요
3. "답변:", "내용:" 등의 접두사 없이 바로 답변 내용만 제공하세요
4. 추측하거나 새로운 내용을 만들어내지 마세요
5. 참고자료가 부족하면 "해당 부분에 대한 정보가 부족합니다"라고 하세요

[참고자료]
{context_info}

[질문]
{user_question}

참고자료를 바탕으로 간결하게 답변하되, "답변:" 같은 접두사 없이 내용만 제공하세요.
"""

        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "당신은 정확성을 최우선으로 하는 어시스턴트입니다. "
                        "제공된 참고자료의 내용을 기반으로 답변하되, "
                        "참고자료에 없는 내용은 절대 추가하지 않습니다. "
                        "간결하고 직접적인 답변을 제공하며, '답변:', '내용:' 등의 접두사 없이 내용만 제공합니다."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.1,  # 낮은 temperature로 일관성 보장
            max_tokens=800,
        )

        return response.choices[0].message.content.strip()

    except Exception as e:
        logging.error(f"RAG 응답 생성 실패: {str(e)}")
        return "답변 생성 중 오류가 발생했습니다. 다시 시도해 주세요."


def generate_qa_id() -> str:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    unique_id = str(uuid.uuid4())[:8]
    return f"qa_{timestamp}_{unique_id}"


@router.post("/qa/store", response_model=QAStoreResponse)
async def store_qa(request: QAStoreRequest):
    try:
        qa_id = generate_qa_id()
        # 질문 가중치 증가로 검색 정확도 향상
        question_weighted = f"질문: {request.question} {request.question} {request.question}"
        combined_text = f"{question_weighted}\n답변: {request.answer}"
        embedding = generate_embedding(combined_text)

        metadata = {
            "qa_id": qa_id,
            "question": request.question,
            "answer": request.answer,
            "created_at": datetime.now().isoformat(),
            "type": "qa_pair",
            "keywords": " ".join(extract_keywords(request.question)),  # 키워드 저장
        }

        index = get_pinecone_index()
        index.upsert(vectors=[(qa_id, embedding, metadata)], namespace=QA_NAMESPACE)

        logging.info(f"QA 저장 완료: {qa_id}")

        return QAStoreResponse(
            success=True, qa_id=qa_id, message="질문-답변이 성공적으로 저장되었습니다."
        )

    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"QA 저장 실패: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"저장 중 오류가 발생했습니다: {str(e)}"
        )


@router.post("/qa/query", response_model=QAQueryResponse)
async def query_qa(request: QAQueryRequest):
    try:
        # 검색 쿼리 최적화
        search_text = f"질문: {request.question} {request.question} {' '.join(extract_keywords(request.question))}"
        question_embedding = generate_embedding(search_text)
        filter_conditions = {"type": "qa_pair"}

        index = get_pinecone_index()
        search_results = index.query(
            vector=question_embedding,
            top_k=15,  # 더 많은 결과 검색 후 필터링
            include_metadata=True,
            filter=filter_conditions,
            namespace=QA_NAMESPACE,
        )

        results = []
        for match in search_results.matches:
            metadata = match.metadata
            result = QAResult(
                qa_id=metadata["qa_id"],
                question=metadata["question"],
                answer=metadata["answer"],
                similarity_score=round(match.score, 4),
                created_at=metadata.get("created_at"),
            )
            results.append(result)

        # 개선된 RAG 응답 생성
        rag_response = generate_rag_response(request.question, results)
        
        # 관련성 있는 결과만 반환
        relevant_results = filter_relevant_results(request.question, results)

        return QAQueryResponse(
            success=True,
            total_found=len(results),
            results=relevant_results[:3],  # 상위 3개만 반환
            rag_response=rag_response,
            message=f"참고자료 {len(relevant_results)}개를 활용하여 답변을 생성했습니다.",
        )

    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"QA 검색 실패: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"검색 중 오류가 발생했습니다: {str(e)}"
        )


@router.get("/qa/list", response_model=QAListResponse)
async def list_qa(offset: int = 0, limit: int = 50):
    try:
        if limit > 100:
            limit = 100

        filter_conditions = {"type": "qa_pair"}
        index = get_pinecone_index()
        dummy_embedding = [0.0] * 1536
        search_results = index.query(
            vector=dummy_embedding,
            top_k=min(1000, offset + limit),
            include_metadata=True,
            filter=filter_conditions,
            namespace=QA_NAMESPACE,
        )

        all_results = []
        for match in search_results.matches:
            metadata = match.metadata
            result = QAResult(
                qa_id=metadata["qa_id"],
                question=metadata["question"],
                answer=metadata["answer"],
                similarity_score=0.0,
                created_at=metadata.get("created_at"),
            )
            all_results.append(result)

        all_results.sort(key=lambda x: x.created_at or "", reverse=True)
        paginated_results = all_results[offset : offset + limit]

        return QAListResponse(
            success=True, total_count=len(all_results), results=paginated_results
        )

    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"QA 목록 조회 실패: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"목록 조회 중 오류가 발생했습니다: {str(e)}"
        )


@router.delete("/qa/{qa_id}", response_model=QADeleteResponse)
async def delete_qa(qa_id: str):
    try:
        index = get_pinecone_index()
        fetch_result = index.fetch(ids=[qa_id], namespace=QA_NAMESPACE)

        if qa_id not in fetch_result.vectors:
            raise HTTPException(status_code=404, detail="해당 QA를 찾을 수 없습니다.")

        index.delete(ids=[qa_id], namespace=QA_NAMESPACE)
        logging.info(f"QA 삭제 완료: {qa_id}")

        return QADeleteResponse(success=True, message="QA가 성공적으로 삭제되었습니다.")

    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"QA 삭제 실패: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"삭제 중 오류가 발생했습니다: {str(e)}"
        )


@router.get("/qa/stats")
async def get_qa_stats():
    try:
        index = get_pinecone_index()
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
                "index_name": PINECONE_INDEX_NAME,
                "thresholds": {
                    "min_similarity": MIN_SIMILARITY_THRESHOLD,
                    "max_context_results": MAX_CONTEXT_RESULTS
                }
            },
        )

    except Exception as e:
        logging.error(f"QA 통계 조회 실패: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"통계 조회 중 오류가 발생했습니다: {str(e)}"
        )
