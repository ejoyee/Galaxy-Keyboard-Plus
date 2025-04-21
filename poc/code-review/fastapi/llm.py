import os
from openai import AsyncOpenAI
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise EnvironmentError("❌ OPENAI_API_KEY 환경변수가 설정되어 있지 않습니다.")

client = AsyncOpenAI(api_key=OPENAI_API_KEY)

MAX_TOKENS_PER_CHUNK = 3000  # 토큰 단위 기준 (프롬프트 + 응답 포함)


async def generate_review_prompt_chunked(mr_desc, full_diff_text):
    chunks = split_text_by_token(full_diff_text, max_chars=3500)  # 단순 문자 기준 분할
    responses = []

    for i, chunk in enumerate(chunks):
        print(f"🧠 [OpenAI] GPT 요청 {i+1}/{len(chunks)}...")
        prompt = f"""
[📄 MR 설명]
{mr_desc}

[🔧 변경 요약 - Part {i+1}]
{chunk}

이 변경사항을 기반으로 코드 품질, 보안, 성능, 리팩토링 측면에서 리뷰어처럼 리뷰해줘.
"""
        res = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "당신은 숙련된 코드 리뷰어입니다."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.7,
        )
        responses.append(res.choices[0].message.content.strip())

    return "\n\n".join(responses)


def split_text_by_token(text, max_chars=3500):
    # 단순히 길이 기준으로 문자열 분할
    chunks = []
    while text:
        chunks.append(text[:max_chars])
        text = text[max_chars:]
    return chunks
