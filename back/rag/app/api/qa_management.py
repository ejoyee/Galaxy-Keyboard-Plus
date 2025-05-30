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
            model="text-embedding-3-small", input=text, encoding_format="float"
        )
        return response.data[0].embedding
    except Exception as e:
        logging.error(f"임베딩 생성 실패: {str(e)}")
        raise HTTPException(status_code=500, detail="임베딩 생성에 실패했습니다.")


def generate_rag_response(user_question: str, search_results: List[QAResult]) -> str:
    """
    RAG를 활용하여 검색 결과를 바탕으로 사용자 질문에 맞는 응답 생성
    """
    try:
        if not search_results:
            # 검색 결과가 없을 때도 일반적인 응답 제공
            prompt = f"""
당신은 도움이 되는 AI 어시스턴트입니다. 사용자의 질문에 대해 정확하고 유용한 답변을 제공해주세요.

질문: {user_question}

답변: 죄송하지만 정확히 일치하는 정보를 찾지 못했습니다. 하지만 다음과 같이 도움을 드릴 수 있습니다:

1. 질문을 좀 더 구체적으로 다시 작성해 보시기 바랍니다.
2. 키워드를 바꿔서 다시 검색해 보세요.
3. 관련된 다른 질문이 있으시면 언제든 문의해 주세요.

더 자세한 정보가 필요하시면 추가로 질문해 주시기 바랍니다.
"""
        else:
            # 검색 결과가 있을 때 RAG 응답 생성
            context_info = ""
            for i, result in enumerate(search_results, 1):
                context_info += f"""
참고 정보 {i} (유사도: {result.similarity_score}):
질문: {result.question}
답변: {result.answer}

"""

            prompt = f"""
당신은 전문적이고 도움이 되는 AI 어시스턴트입니다. 아래 제공된 참고 정보를 바탕으로 사용자의 질문에 대해 정확하고 이해하기 쉽이 답변하세요.

=== 참고 정보 ===
{context_info}
=== 사용자 질문 ===
{user_question}

=== 답변 지침 ===
1. 참고 정보를 기반으로 사용자 질문에 직접적이고 유용한 답변을 제공하세요.
2. 여러 참고 정보가 있다면 종합하여 완전하고 일관된 답변을 만드세요.
3. 기술적 내용이라면 구체적인 예시나 코드를 포함하세요.
4. 단계별 설명이 필요한 경우 순서대로 나열하세요.
5. 참고 정보만으로 완전한 답변이 어려우면, 가능한 범위에서 최선의 답변을 제공하고 추가 정보가 필요함을 안내하세요.
6. 답변은 명확하고 정확하며 실용적이어야 합니다.
7. 한국어로 자연스럽게 답변하세요.

답변:
"""

        # OpenAI GPT를 사용하여 응답 생성
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "당신은 도움이 되는 AI 어시스턴트입니다. 제공된 정보를 바탕으로 정확하고 유용한 답변을 제공합니다.",
                },
                {"role": "user", "content": prompt},
            ],
            max_tokens=1000,
            temperature=0.3,
        )

        return response.choices[0].message.content.strip()

    except Exception as e:
        logging.error(f"RAG 응답 생성 실패: {str(e)}")
        # 오류 발생 시 기본 응답 제공
        return f"죄송합니다. 답변 생성 중 오류가 발생했습니다. 질문 '{user_question}'에 대해 다시 시도해 주시거나, 질문을 다르게 표현해 보시기 바랍니다."


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
            "type": "qa_pair",
        }

        # Pinecone에 저장
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
    """
    질문에 대한 유사한 답변을 검색하고 RAG 기반 응답을 생성합니다.

    - **question**: 검색할 질문 (1-1000자)

    **반환 내용:**
    - 검색된 관련 QA 목록
    - RAG를 활용한 사용자 질문에 맞춤 생성 답변
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
            namespace=QA_NAMESPACE,
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
                created_at=metadata.get("created_at"),
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

        # RAG 응답 생성
        rag_response = generate_rag_response(request.question, results)
        logging.info(f"RAG 응답 생성 완료: {len(rag_response)} 문자")

        return QAQueryResponse(
            success=True,
            total_found=len(results),
            results=results,
            rag_response=rag_response,
            message=message,
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
            namespace=QA_NAMESPACE,
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
                created_at=metadata.get("created_at"),
            )
            all_results.append(result)

        # 생성일시 기준 정렬 (최신순)
        all_results.sort(key=lambda x: x.created_at or "", reverse=True)

        # 페이지네이션 적용
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
                "index_name": PINECONE_INDEX_NAME,
            },
        )

    except Exception as e:
        logging.error(f"QA 통계 조회 실패: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"통계 조회 중 오류가 발생했습니다: {str(e)}"
        )
