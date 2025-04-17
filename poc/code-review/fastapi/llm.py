import os
import openai

openai.api_key = os.getenv("OPENAI_API_KEY")


async def generate_review_prompt(mr_desc, changes_summary):
    prompt = f"""
[📄 MR 설명]
{mr_desc}

[🔧 변경 요약]
{changes_summary}

이 변경사항을 기반으로 코드 품질, 보안, 성능, 리팩토링 측면에서 리뷰어처럼 리뷰해줘.
"""
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "당신은 숙련된 코드 리뷰어입니다."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.7,
    )
    return response["choices"][0]["message"]["content"]
