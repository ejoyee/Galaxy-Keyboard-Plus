from fastapi import FastAPI, Request
from pydantic import BaseModel
from dotenv import load_dotenv
from review import handle_merge_request
from typing import Dict, Any

load_dotenv()

app = FastAPI()


# Pydantic 모델 추가: Swagger에서 요청 본문 입력 가능하게 함
class GitLabWebhookPayload(BaseModel):
    object_kind: str
    project: Dict[str, Any]
    object_attributes: Dict[str, Any]


@app.post("/gitlab/webhook")
async def gitlab_webhook(payload: GitLabWebhookPayload):
    # Pydantic 모델로 변환된 payload를 dict로 변환하여 사용
    event = payload.model_dump()
    if event.get("object_kind") == "merge_request":
        await handle_merge_request(event)
    return {"status": "ok"}
