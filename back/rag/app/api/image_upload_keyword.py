from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from app.utils.image_captioner import generate_image_caption
import json
import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
router = APIRouter()


@router.post("/upload-image-keyword/")
async def upload_image_keyword(
    user_id: str = Form(...),
    access_id: str = Form(...),
    file: UploadFile = File(...),
):
    try:
        image_bytes = await file.read()

        # 1. 이미지 캡션 생성
        caption = generate_image_caption(image_bytes)

        # 2. OpenAI를 통해 키워드 추출 요청
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

        prompt = (
            f"다음 사진 설명을 보고 사람들이 검색할 수 있는 키워드를 가능한 많이 추출해줘. "
            f"각 키워드는 한 단어로 된 명사 위주로 해줘. 중복 없이 출력하고, 결과는 JSON 배열로 줘. "
            f'예시: ["노트북", "회의", "커피"]\n\n'
            f"설명: {caption}"
        )

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "너는 키워드 추출 전문가야."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
        )

        keywords_raw = response.choices[0].message.content

        try:
            keywords = json.loads(keywords_raw)
        except json.JSONDecodeError:
            # JSON 형식이 아닐 경우 수동 파싱
            keywords = [
                kw.strip().strip('"')
                for kw in keywords_raw.strip("[]").split(",")
                if kw.strip()
            ]

        return {
            "user_id": user_id,
            "access_id": access_id,
            "caption": caption,
            "keywords": keywords,
            "status": "success",
        }

    except Exception as e:
        return {
            "user_id": user_id,
            "access_id": access_id,
            "status": "error",
            "message": str(e),
        }
