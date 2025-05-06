import logging
from fastapi import APIRouter, UploadFile, File, Form
from app.utils.image_classifier import classify_image_from_bytes
from app.utils.image_captioner import generate_image_caption
from app.utils.image_text_extractor import extract_text_from_image
from app.utils.vector_store import save_text_to_pinecone

# 로거 설정
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
    image_id: str = Form(...),
    file: UploadFile = File(...),
):
    try:
        logger.info(f"📥 이미지 처리 시작 - user_id={user_id}, image_id={image_id}")

        image_bytes = await file.read()
        text_score = classify_image_from_bytes(image_bytes)
        logger.info(f"🔍 이미지 분류 점수: {text_score:.3f} (image_id={image_id})")

        if text_score < 0.1:
            description = generate_image_caption(image_bytes)
            target = "photo"
            text = f"{image_id}: {description}"
            logger.info(f"🖼️ 이미지 설명 생성 완료 - {description}")
        else:
            extracted_text = extract_text_from_image(image_bytes)
            target = "info"
            text = f"{image_id}: {extracted_text}"
            logger.info(f"📝 텍스트 추출 완료 - {extracted_text}")

        namespace = save_text_to_pinecone(user_id, text, target)
        logger.info(f"✅ 벡터 저장 완료 - namespace={namespace}")

        return {
            "image_id": image_id,
            "type": target,
            "namespace": namespace,
            "content": text,
            "status": "success",
        }

    except Exception as e:
        logger.error(f"❌ 처리 중 오류 발생 (image_id={image_id}): {e}")
        return {"image_id": image_id, "status": "error", "message": str(e)}
