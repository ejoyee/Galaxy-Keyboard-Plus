# app/utils/image_captioner.py

import base64
import os
import io
from PIL import Image
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def resize_image(image_bytes: bytes, max_size=(512, 512)) -> bytes:
    """이미지 해상도를 줄여서 비용 절감"""
    image = Image.open(io.BytesIO(image_bytes))
    image.thumbnail(max_size)  # aspect ratio 유지
    output = io.BytesIO()
    image.save(output, format="JPEG")
    return output.getvalue()


def generate_image_caption(image_bytes: bytes) -> str:
    # 비용 절감을 위해 해상도 축소
    resized_bytes = resize_image(image_bytes)

    # base64 인코딩
    encoded_image = base64.b64encode(resized_bytes).decode("utf-8")

    response = client.chat.completions.create(
        model="gpt-4-turbo",
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "이 이미지를 짧고 간결하게 설명해줘. 중요한 사물이나 동물, 위치만 말해줘.",
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
        max_tokens=200,  # 출력 길이 제한해서 비용 절감
    )

    return response.choices[0].message.content.strip()
