import os
from uuid import uuid4
from dotenv import load_dotenv
from pinecone import Pinecone
from app.utils.embedding import get_text_embedding

load_dotenv()

pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
index = pc.Index(os.getenv("PINECONE_INDEX_NAME"))


def save_text_to_pinecone(user_id: str, text: str, target: str) -> str:
    """
    user_id와 target (photo/text)에 따라 지정된 네임스페이스로 텍스트 저장
    """
    namespace = f"{user_id}_{target}"
    vector = get_text_embedding(text)

    index.upsert(
        vectors=[
            {
                "id": str(uuid4()),
                "values": vector,
                "metadata": {"text": text},
            }
        ],
        namespace=namespace,
    )

    return namespace
