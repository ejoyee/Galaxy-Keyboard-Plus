import os
import re
from dotenv import load_dotenv
from typing import Literal
from app.utils.embedding import get_text_embedding
from pinecone import Pinecone
from openai import OpenAI
from app.utils.chat_vector_store import search_chat_history
import json

load_dotenv()

pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
index = pc.Index(os.getenv("PINECONE_INDEX_NAME"))
openai = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def determine_query_type(query: str) -> Literal["photo", "info", "ambiguous"]:
    """질문이 사진 관련인지 정보 관련인지 판별"""
    response = openai.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": (
                    "사용자의 질문이 사진(이미지)을 찾으려는 것인지, "
                    "정보(텍스트/일정)를 찾으려는 것인지, 혹은 애매한지를 판단해줘. "
                    "'photo', 'info', 'ambiguous' 중 하나로만 응답해."
                ),
            },
            {"role": "user", "content": query},
        ],
        max_tokens=10,
    )
    answer = response.choices[0].message.content.strip().lower()
    if answer not in {"photo", "info", "ambiguous"}:
        return "ambiguous"
    return answer


def search_similar_items(
    user_id: str, query: str, target: str, top_k: int = 5
) -> list[dict]:
    """Pinecone에서 해당 네임스페이스로 유사 항목 검색"""
    namespace = f"{user_id}_{target}"
    vector = get_text_embedding(query)

    response = index.query(
        vector=vector,
        namespace=namespace,
        top_k=top_k,
        include_metadata=True,
    )

    results = []
    for match in response["matches"]:
        full_text = match["metadata"].get("text", "")
        if ": " in full_text:
            image_id, description = full_text.split(": ", 1)
        else:
            image_id, description = "unknown", full_text  # fallback

        image_id = re.sub(r"\s*\([^)]*\)", "", image_id).strip()

        results.append(
            {
                "score": round(match["score"], 3),
                "id": image_id,
                "text": description,
            }
        )

    return results


def generate_answer_from_info(query: str, results: list[dict]) -> str:
    """유사한 정보 결과를 바탕으로 LLM이 답변 생성"""
    context = "\n".join([f"- {item['text']}" for item in results])
    prompt = f"""다음은 참고할 정보들입니다:

{context}

사용자 질문: "{query}"

이 정보를 기반으로 사용자 질문에 답변해줘."""

    response = openai.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=300,
    )

    return response.choices[0].message.content.strip()


def generate_answer_with_context(
    user_id: str, query: str, info_results: list[dict]
) -> str:
    # chat history 불러오기
    history = search_chat_history(user_id, query, top_k=5)

    history_text = "\n".join([f"{h['role']}: {h['text']}" for h in history])
    info_text = "\n".join([f"- {item['text']}" for item in info_results])

    prompt = f"""아래는 이전 대화 기록입니다:
{history_text}

다음은 참고할 정보들입니다:
{info_text}

사용자 질문: "{query}"

이 모든 내용을 바탕으로 사용자 질문에 대해 정확하고 간결하게 답변해줘."""

    response = openai.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=300,
    )

    return response.choices[0].message.content.strip()


def generate_combined_answer_with_context(
    user_id: str, query: str, info_results: list[dict], photo_results: list[dict]
) -> dict:
    """정보 + 이미지 설명을 바탕으로 종합 답변 생성"""
    history = search_chat_history(user_id, query, top_k=5)

    history_text = "\n".join([f"{h['role']}: {h['text']}" for h in history])
    info_text = "\n".join([f"- {item['text']}" for item in info_results])
    photo_text = "\n".join(
        [f"- {item['id']}: {item['text']}" for item in photo_results]
    )

    prompt = f"""아래는 이전 대화 기록입니다:
{history_text}

다음은 참고할 정보들입니다:
{info_text}

다음은 관련된 사진 설명입니다:
{photo_text}

사용자 질문: "{query}"

위의 모든 내용을 바탕으로 사용자 질문에 정확하게 답변해줘."""

    response = openai.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=400,
    )

    return {
        "answer": response.choices[0].message.content.strip(),
        "photo_results": photo_results,
        "info_results": info_results,
    }


def filter_relevant_items_with_llm(
    query: str, items: list[dict], item_type: str
) -> list[dict]:
    """
    LLM에게 항목 중 질문과 관련 있는 것만 추려달라고 요청
    item_type: "정보" 또는 "사진"
    """
    bullet_list = "\n".join([f"- {item['id']}: {item['text']}" for item in items])
    prompt = f"""
다음은 사용자의 질문입니다:
"{query}"

다음은 {item_type} 항목 리스트입니다:
{bullet_list}

이 중 질문과 직접 관련이 있는 항목만 골라줘. 
그 항목들의 ID만 리스트 형태로 반환해줘. (예: ["123", "456"])
    """.strip()

    response = openai.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=100,
        temperature=0.3,
    )

    try:
        relevant_ids = json.loads(response.choices[0].message.content.strip())
        return [item for item in items if item["id"] in relevant_ids]
    except Exception:
        # 실패 시 전체 반환
        return items


def extract_personal_info_context(history: list[dict]) -> str:
    # 예시: 이름, 애완동물, 선호 등 추론
    notes_text = "\n".join([f"{h['role']}: {h['text']}" for h in history])

    prompt = f"""아래 대화에서 사용자의 개인화 정보(이름, 가족, 반려동물, 일정 등)를 요약해줘.
문장이 아닌 키워드 또는 간단한 문장으로 적어줘.

대화:
{notes_text}
"""
    response = openai.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=100,
    )
    return response.choices[0].message.content.strip()


def enhance_query_with_personal_context(user_id: str, query: str) -> str:
    # 과거 대화 기반 개인 정보 요약
    history = search_chat_history(user_id, query, top_k=20)
    personal_context = extract_personal_info_context(history)

    if personal_context:
        return f"{query}\n\n(참고: {personal_context})"
    return query
