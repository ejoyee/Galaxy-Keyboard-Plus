from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from app.utils.image_captioner import generate_image_caption
import json
import os
import psycopg2
from openai import OpenAI
from dotenv import load_dotenv
from datetime import datetime
import traceback

load_dotenv()
router = APIRouter()

# DB 연결 설정
DB_PARAMS = {
    "host": "3.38.95.110",
    "port": "5434",
    "database": os.getenv("POSTGRES_RAG_DB_NAME"),
    "user": os.getenv("POSTGRES_RAG_USER"),
    "password": os.getenv("POSTGRES_RAG_PASSWORD"),
}


@router.post("/upload-image-keyword/")
async def upload_image_keyword(
    user_id: str = Form(...),
    access_id: str = Form(...),
    file: UploadFile = File(...),
):
    try:
        print("🔍 DB_PARAMS = ", DB_PARAMS)

        connection = psycopg2.connect(**DB_PARAMS)
        cursor = connection.cursor()

        # access_id 중복 체크
        check_query = "SELECT id FROM images WHERE access_id = %s;"
        cursor.execute(check_query, (access_id,))
        existing = cursor.fetchone()

        if existing:
            cursor.close()
            connection.close()
            return {
                "user_id": user_id,
                "access_id": access_id,
                "status": "skipped",
                "message": "이미 등록된 이미지입니다.",
            }

        image_bytes = await file.read()

        # 1. 이미지 캡션 생성
        caption = generate_image_caption(image_bytes)

        # 2. OpenAI로 키워드 추출
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        prompt = (
            f"다음 사진 설명을 보고 사람들이 검색할 수 있는 키워드를 가능한 많이 추출해줘. "
            f"각 키워드는 한 단어로 된 명사 위주로 해줘. 중복 없이 출력하고, 결과는 JSON 배열로 줘. "
            f'예시: ["노트북", "회의", "커피"]\n\n'
            f"설명: {caption}"
        )

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "너는 키워드 추출 전문가야. 출력은 JSON 배열로만 해. 마크다운 코드블록 쓰지 마.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
        )

        keywords_raw = response.choices[0].message.content

        # 코드블록(````json ... `````) 제거
        if keywords_raw.startswith("```"):
            keywords_raw = keywords_raw.strip("`").strip()
            # 혹시라도 "json\n[..." 같이 시작되면 제거
            if keywords_raw.lower().startswith("json"):
                keywords_raw = keywords_raw[4:].strip()

        try:
            keywords = json.loads(keywords_raw)
        except json.JSONDecodeError:
            keywords = [
                kw.strip().strip('"')
                for kw in keywords_raw.strip("[]").split(",")
                if kw.strip()
            ]

        # 3. DB 저장

        now = datetime.utcnow()

        # 이미지 정보 INSERT (중복 access_id 시 conflict 무시)
        insert_image_query = """
        INSERT INTO images (user_id, access_id, caption, image_time)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (access_id) DO UPDATE SET caption = EXCLUDED.caption
        RETURNING id;
        """
        cursor.execute(insert_image_query, (user_id, access_id, caption, now))
        image_id = cursor.fetchone()[0]

        # 키워드 INSERT
        insert_keyword_query = """
        INSERT INTO image_keywords (image_id, keyword, created_at)
        VALUES (%s, %s, %s);
        """
        for keyword in keywords:
            cursor.execute(insert_keyword_query, (image_id, keyword, now))

        connection.commit()
        cursor.close()
        connection.close()

        return {
            "user_id": user_id,
            "access_id": access_id,
            "caption": caption,
            "keywords": keywords,
            "status": "success",
        }

    except Exception as e:
        print("❌ 예외 발생:")
        traceback.print_exc()  # 콘솔에 전체 스택트레이스 출력
        return {
            "user_id": user_id,
            "access_id": access_id,
            "status": "error",
            "message": str(e) or repr(e),
        }
