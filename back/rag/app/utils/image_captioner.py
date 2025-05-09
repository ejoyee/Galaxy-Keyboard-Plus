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

    # RGBA 또는 기타 비-JPEG 호환 모드일 경우 RGB로 변환
    if image.mode != "RGB":
        image = image.convert("RGB")

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
        model="gpt-4o-mini",
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": (
                            "이 이미지를 자세히 설명해줘. 사진 속에 보이는 사물, 인물, 동물, 배경, 위치, 색감, 분위기 등을 가능한 한 구체적으로 묘사해줘. "
                            "사진의 주요 구성 요소와 그 관계도 설명해줘. 불분명한 부분은 추정해서 말해줘도 돼."
                        ),
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
    )

    return response.choices[0].message.content.strip()
