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
MIN_SIMILARITY_THRESHOLD = 0.25  # 더 관대한 임계값
MAX_CONTEXT_RESULTS = 8  # 더 많은 컨텍스트 활용
DEBUG_MODE = True  # 디버깅 모드


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
    stopwords = {
        "은", "는", "이", "가", "을", "를", "에", "에서", "로", "으로",
        "와", "과", "도", "만", "부터", "까지", "의", "에게", "께", "한테",
        "어떻게", "무엇", "언제", "어디", "왜", "누구", "얼마", "어느",
        "대한", "가지", "수", "있습니다", "있는", "있어요", "하는", "됩니다"
    }
    
    # 문장부호 제거 후 단어 추출
    text_clean = re.sub(r'[^\w\s가-힣]', ' ', text)
    words = re.findall(r"[가-힣a-zA-Z0-9]+", text_clean)
    keywords = [word for word in words if word not in stopwords and len(word) >= 2]
    
    # 중요 키워드 추가 검사
    important_keywords = ['보안', 'security', '암호화', '인증', '키보드', '개인정보', '데이터']
    for keyword in important_keywords:
        if keyword in text.lower():
            keywords.append(keyword)
    
    return list(set(keywords))  # 중복 제거


def filter_relevant_results(
    question: str, search_results: List[QAResult]
) -> List[QAResult]:
    """관련성 있는 결과만 필터링"""
    if not search_results:
        return []

    question_keywords = set(extract_keywords(question))
    filtered_results = []
    
    if DEBUG_MODE:
        logging.info(f"키워드 추출 결과: {question_keywords}")
        logging.info(f"검색된 전체 결과수: {len(search_results)}")

    for i, result in enumerate(search_results):
        include_reason = None
        
        # 유사도 기본 필터링
        if result.similarity_score >= MIN_SIMILARITY_THRESHOLD:
            include_reason = f"유사도 {result.similarity_score:.4f}"
            filtered_results.append(result)
        else:
            # 키워드 매칭으로 추가 검증
            result_keywords = set(extract_keywords(result.question + " " + result.answer))
            common_keywords = question_keywords.intersection(result_keywords)
            
            if common_keywords:
                include_reason = f"키워드 매칭: {common_keywords}"
                filtered_results.append(result)
        
        if DEBUG_MODE and include_reason:
            logging.info(f"결과 {i+1} 포함: {include_reason} - {result.question[:50]}...")
        elif DEBUG_MODE:
            logging.info(f"결과 {i+1} 제외: 유사도 {result.similarity_score:.4f} - {result.question[:50]}...")

    if DEBUG_MODE:
        logging.info(f"필터링 후 결과수: {len(filtered_results)}")
        
    return filtered_results[:MAX_CONTEXT_RESULTS]


def generate_rag_response(user_question: str, search_results: List[QAResult]) -> str:
    try:
        # 관련성 있는 결과 필터링
        relevant_results = filter_relevant_results(user_question, search_results)

        if not relevant_results:
            return "해당 질문에 대한 구체적인 정보가 준비되어 있지 않습니다. 다른 질문이 있으시면 답변드리겠습니다."

        # 컨텍스트 구성
        context_info = "\n".join(
            f"참고자료 {i+1}:\n질문: {r.question}\n답변: {r.answer}\n"
            for i, r in enumerate(relevant_results)
        )

        prompt = f"""
당신은 삼성 청년 소프트웨어 아카데미 프로젝트 발표 Q&A를 담당합니다.
아래 참고자료의 내용과 말투를 그대로 활용하여 질문에 답변하세요.

[중요 규칙]
1. 참고자료에 있는 내용만 사용하세요
2. 참고자료의 담백하고 직접적인 말투를 유지하세요
3. 추측하거나 새로운 내용을 만들어내지 마세요
4. 참고자료가 부족하면 "해당 부분에 대한 정보가 부족합니다"라고 하세요

[참고자료]
{context_info}

[질문]
{user_question}

참고자료의 답변 스타일을 그대로 따라하여 간결하고 담백하게 답변하세요.
"""

        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "당신은 정확성을 최우선으로 하는 어시스턴트입니다. "
                        "제공된 참고자료의 내용과 말투를 정확히 따라하되, "
                        "참고자료에 없는 내용은 절대 추가하지 않습니다. "
                        "간결하고 담백한 답변을 제공합니다."
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
        # 저장 시와 검색 시 일관된 임베딩 생성
        keywords = extract_keywords(request.question)
        question_weighted = f"질문: {request.question} {request.question} {' '.join(keywords)}"
        combined_text = f"{question_weighted}\n답변: {request.answer}"
        embedding = generate_embedding(combined_text)
        
        if DEBUG_MODE:
            logging.info(f"저장 중 QA ID: {qa_id}")
            logging.info(f"저장 중 키워드: {keywords}")
            logging.info(f"저장 중 임베딩 텍스트: {combined_text[:100]}...")

        metadata = {
            "qa_id": qa_id,
            "question": request.question,
            "answer": request.answer,
            "created_at": datetime.now().isoformat(),
            "type": "qa_pair",
            "keywords": " ".join(keywords),  # 키워드 저장
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
        # 저장 시와 동일한 방식으로 검색 쿼리 생성
        keywords = extract_keywords(request.question)
        search_text = f"질문: {request.question} {request.question} {' '.join(keywords)}"
        question_embedding = generate_embedding(search_text)
        filter_conditions = {"type": "qa_pair"}
        
        if DEBUG_MODE:
            logging.info(f"검색 질문: {request.question}")
            logging.info(f"검색 키워드: {keywords}")
            logging.info(f"검색 임베딩 텍스트: {search_text}")

        index = get_pinecone_index()
        search_results = index.query(
            vector=question_embedding,
            top_k=20,  # 더 많은 결과 검색 후 필터링
            include_metadata=True,
            filter=filter_conditions,
            namespace=QA_NAMESPACE,
        )
        
        if DEBUG_MODE:
            logging.info(f"전체 검색 결과 수: {len(search_results.matches)}")
            for i, match in enumerate(search_results.matches[:5]):
                logging.info(f"상위 {i+1}: {match.score:.4f} - {match.metadata['question'][:50]}...")

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
            
            if DEBUG_MODE:
                logging.info(f"QA 결과: {match.score:.4f} - {metadata['question'][:30]}... - 키워드: {metadata.get('keywords', 'N/A')}")

        # 개선된 RAG 응답 생성
        rag_response = generate_rag_response(request.question, results)

        # 관련성 있는 결과만 반환
        relevant_results = filter_relevant_results(request.question, results)

        return QAQueryResponse(
            success=True,
            total_found=len(results),
            results=relevant_results[:5],  # 상위 5개 반환
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
                    "max_context_results": MAX_CONTEXT_RESULTS,
                },
                "debug_mode": DEBUG_MODE,
            },
        )

    except Exception as e:
        logging.error(f"QA 통계 조회 실패: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"통계 조회 중 오류가 발생했습니다: {str(e)}"
        )


@router.get("/qa/debug/{qa_id}")
async def debug_qa_embedding(qa_id: str):
    """특정 QA의 임베딩 정보를 확인하는 디버깅 엔드포인트"""
    try:
        index = get_pinecone_index()
        fetch_result = index.fetch(ids=[qa_id], namespace=QA_NAMESPACE)
        
        if qa_id not in fetch_result.vectors:
            raise HTTPException(status_code=404, detail="해당 QA를 찾을 수 없습니다.")
        
        vector_data = fetch_result.vectors[qa_id]
        metadata = vector_data.metadata
        
        # 키워드 재추출 테스트
        current_keywords = extract_keywords(metadata["question"])
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "qa_id": qa_id,
                "question": metadata["question"],
                "answer": metadata["answer"],
                "stored_keywords": metadata.get("keywords", "").split(),
                "current_extracted_keywords": current_keywords,
                "created_at": metadata.get("created_at"),
                "vector_dimension": len(vector_data.values),
            },
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"QA 디버깅 실패: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"디버깅 중 오류가 발생했습니다: {str(e)}"
        )


@router.post("/qa/debug/search")
async def debug_search(request: QAQueryRequest):
    """검색 과정을 상세히 디버깅하는 엔드포인트"""
    try:
        keywords = extract_keywords(request.question)
        search_text = f"질문: {request.question} {request.question} {' '.join(keywords)}"
        question_embedding = generate_embedding(search_text)
        
        index = get_pinecone_index()
        search_results = index.query(
            vector=question_embedding,
            top_k=50,  # 모든 결과 확인
            include_metadata=True,
            filter={"type": "qa_pair"},
            namespace=QA_NAMESPACE,
        )
        
        all_results = []
        for match in search_results.matches:
            metadata = match.metadata
            result_keywords = extract_keywords(metadata["question"] + " " + metadata["answer"])
            common_keywords = set(keywords).intersection(set(result_keywords))
            
            all_results.append({
                "qa_id": metadata["qa_id"],
                "question": metadata["question"],
                "answer": metadata["answer"][:100] + "...",
                "similarity_score": round(match.score, 4),
                "stored_keywords": metadata.get("keywords", "").split(),
                "extracted_keywords": result_keywords,
                "common_keywords": list(common_keywords),
                "passes_threshold": match.score >= MIN_SIMILARITY_THRESHOLD,
                "has_keyword_match": bool(common_keywords),
            })
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "search_question": request.question,
                "search_keywords": keywords,
                "search_text": search_text,
                "threshold": MIN_SIMILARITY_THRESHOLD,
                "total_found": len(all_results),
                "results": all_results,
            },
        )
        
    except Exception as e:
        logging.error(f"검색 디버깅 실패: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"검색 디버깅 중 오류가 발생했습니다: {str(e)}"
        )
