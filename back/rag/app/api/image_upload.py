import logging
import httpx
import json
from datetime import datetime
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from app.utils.image_classifier import classify_image_from_bytes
from app.utils.image_captioner import generate_image_caption
from app.utils.image_text_extractor import extract_text_from_image
from app.utils.vector_store import save_text_to_pinecone
from app.utils.schedule_parser import extract_schedule

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
console_handler = logging.StreamHandler()
formatter = logging.Formatter("[%(asctime)s] %(levelname)s - %(message)s")
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

router = APIRouter()


@router.post("/upload-image/")
async def upload_image(
    user_id: str = Form(...),
    access_id: str = Form(...),
    image_time: datetime = Form(...),  # ✅ datetime으로 직접 받기
    file: UploadFile = File(...),
):
    try:
        logger.info(f"📥 이미지 처리 시작 - user_id={user_id}, access_id={access_id}")

        image_bytes = await file.read()
        text_score = classify_image_from_bytes(image_bytes)
        logger.info(f"🔍 이미지 분류 점수: {text_score:.3f} (access_id={access_id})")

        if text_score < 0.1:
            description = generate_image_caption(image_bytes)
            target = "photo"
            content = description
            logger.info(f"🖼️ 이미지 설명 생성 완료 - {description}")
        else:
            extracted_text = extract_text_from_image(image_bytes)
            target = "info"
            content = extracted_text
            logger.info(f"📝 텍스트 추출 완료 - {extracted_text}")

        text_for_embedding = f"{access_id} ({image_time.isoformat()}): {content}"
        namespace = save_text_to_pinecone(user_id, text_for_embedding, target)
        logger.info(f"✅ 벡터 저장 완료 - namespace={namespace}")

        image_payload = {
            "userId": user_id,
            "accessId": access_id,
            "imageTime": image_time.isoformat(),  # ✅ ISO 포맷으로 직렬화
            "type": target,
            "content": content,
        }

        async with httpx.AsyncClient() as client:
            logger.info(f"📤 이미지 정보 전송 → payload: {image_payload}")
            logger.info(
                f"📤 이미지 전송 바디(JSON):\n{json.dumps(image_payload, ensure_ascii=False, indent=2)}"
            )

            image_response = await client.post(
                "http://backend-service:8083/api/v1/images", json=image_payload
            )
            logger.info(f"📥 이미지 응답 상태: {image_response.status_code}")
            logger.debug(f"📥 이미지 응답 내용: {image_response.text}")

            if image_response.status_code != 200:
                logger.error(f"❌ 이미지 정보 저장 실패: {image_response.text}")
                raise HTTPException(status_code=500, detail="이미지 정보 저장 실패")

            image_id = image_response.json().get("result", {}).get("imageId")

            if target == "info":
                schedule_result = extract_schedule(content)
                if schedule_result.get("is_schedule") and schedule_result.get(
                    "datetime"
                ):
                    plan_payload = {
                        "userId": user_id,
                        "planTime": schedule_result["datetime"],  # 이미 ISO8601 형식임
                        "planContent": schedule_result.get("event", content),
                        "imageId": image_id,
                    }

                    logger.info(f"📤 일정 등록 전송 → payload: {plan_payload}")
                    logger.info(
                        f"📤 일정 전송 바디(JSON):\n{json.dumps(plan_payload, ensure_ascii=False, indent=2)}"
                    )

                    plan_response = await client.post(
                        "http://backend-service:8083/api/v1/plans", json=plan_payload
                    )
                    logger.info(f"📥 일정 응답 상태: {plan_response.status_code}")
                    logger.debug(f"📥 일정 응답 내용: {plan_response.text}")

                    if plan_response.status_code != 200:
                        logger.warning(f"⚠️ 일정 등록 실패: {plan_response.text}")
                    else:
                        logger.info(f"📅 일정 등록 완료: {plan_payload}")

        return {
            "access_id": access_id,
            "image_time": image_time.isoformat(),
            "type": target,
            "namespace": namespace,
            "content": text_for_embedding,
            "image_id": image_id,
            "status": "success",
        }

    except Exception as e:
        logger.error(f"❌ 처리 중 오류 발생 (access_id={access_id}): {e}")
        return {
            "access_id": access_id,
            "image_time": (
                image_time.isoformat()
                if isinstance(image_time, datetime)
                else str(image_time)
            ),
            "status": "error",
            "message": str(e),
        }
