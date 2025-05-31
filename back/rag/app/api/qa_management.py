from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
import os
import uuid
from datetime import datetime
from typing import List
from dotenv import load_dotenv
from pinecone import Pinecone
from openai import OpenAI
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

PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_INDEX_NAME = os.getenv("PINECONE_INDEX_NAME")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
QA_NAMESPACE = "qa_system"

openai_client = OpenAI(api_key=OPENAI_API_KEY)


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


def generate_rag_response(user_question: str, search_results: List[QAResult]) -> str:
    try:
        if not search_results:
            return "죄송합니다. 해당 질문에 대한 정보를 찾을 수 없습니다."

        context_info = "\n".join(
            f"참고 {i}. 질문: {r.question}\n답변: {r.answer}"
            for i, r in enumerate(search_results, 1)
        )

        prompt = f"""
당신은 AI 어시스턴트입니다. 아래 제공된 참고 정보만 바탕으로 사용자 질문에 응답하세요.
참고 정보 외에 추측하거나 새로운 내용을 생성하지 마세요.

[참고 정보]
{context_info}

[사용자 질문]
{user_question}

[답변 규칙]
1. 반드시 참고 정보에 기반해 답변하세요.
2. 참고 정보가 부족하면 "해당 질문에 대한 정보를 찾을 수 없습니다."라고 답변하세요.
3. 문장은 자연스럽고 명확한 한국어로 작성하세요.
"""

        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "당신은 정보 보존에 엄격한 AI 어시스턴트입니다. "
                        "제공된 참고 정보 외에는 어떤 내용도 추론하거나 생성하지 않습니다. "
                        "참고 정보가 부족하면 '해당 질문에 대한 정보를 찾을 수 없습니다'라고 응답해야 합니다."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.0,
            max_tokens=800,
        )

        return response.choices[0].message.content.strip()

    except Exception as e:
        logging.error(f"RAG 응답 생성 실패: {str(e)}")
        return "죄송합니다. 답변 생성 중 오류가 발생했습니다. 다시 시도해 주세요."


def generate_qa_id() -> str:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    unique_id = str(uuid.uuid4())[:8]
    return f"qa_{timestamp}_{unique_id}"


@router.post("/qa/store", response_model=QAStoreResponse)
async def store_qa(request: QAStoreRequest):
    try:
        qa_id = generate_qa_id()
        question_weighted = f"질문: {request.question} {request.question}"
        combined_text = f"{question_weighted}\n답변: {request.answer}"
        embedding = generate_embedding(combined_text)

        metadata = {
            "qa_id": qa_id,
            "question": request.question,
            "answer": request.answer,
            "created_at": datetime.now().isoformat(),
            "type": "qa_pair",
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
        search_text = f"질문: {request.question} {request.question}"
        question_embedding = generate_embedding(search_text)
        filter_conditions = {"type": "qa_pair"}

        index = get_pinecone_index()
        search_results = index.query(
            vector=question_embedding,
            top_k=10,
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

        rag_response = generate_rag_response(request.question, results[:3])

        return QAQueryResponse(
            success=True,
            total_found=len(results),
            results=results[:3],
            rag_response=rag_response,
            message="검색된 결과를 바탕으로 응답을 생성했습니다.",
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
            },
        )

    except Exception as e:
        logging.error(f"QA 통계 조회 실패: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"통계 조회 중 오류가 발생했습니다: {str(e)}"
        )
