# app/utils/image_captioner.py

import base64
import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def generate_image_caption(image_bytes: bytes) -> str:
    # 이미지를 base64로 인코딩
    encoded_image = base64.b64encode(image_bytes).decode("utf-8")

    response = client.chat.completions.create(
        model="gpt-4-turbo",  # ✅ 최신 모델명
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "이 이미지를 설명해줘. 구체적으로 어떤 사물이나 동물이 어디에 있는지 알려줘.",
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{encoded_image}",
                        },
                    },
                ],
            }
        ],
        max_tokens=300,
    )

    return response.choices[0].message.content.strip()
