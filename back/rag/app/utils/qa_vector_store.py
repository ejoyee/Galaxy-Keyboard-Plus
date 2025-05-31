# app/utils/qa_vector_store.py

import os
import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any
from dotenv import load_dotenv
from pinecone import Pinecone
from app.utils.embedding import get_text_embedding
import logging

load_dotenv()

logger = logging.getLogger(__name__)


class QAVectorStore:
    """질문-답변 벡터 저장소 관리 클래스"""
    
    def __init__(self):
        self.api_key = os.getenv("PINECONE_API_KEY")
        self.index_name = os.getenv("PINECONE_INDEX_NAME")
        
        if not self.api_key or not self.index_name:
            raise ValueError("PINECONE_API_KEY와 PINECONE_INDEX_NAME 환경변수가 필요합니다.")
        
        self.pc = Pinecone(api_key=self.api_key)
        self.index = self.pc.Index(self.index_name)
    
    def generate_qa_id(self) -> str:
        """고유한 QA ID 생성"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_id = str(uuid.uuid4())[:8]
        return f"qa_{timestamp}_{unique_id}"
    
    def store_qa(
        self, 
        question: str, 
        answer: str, 
        category: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> str:
        """질문-답변을 벡터 저장소에 저장"""
        try:
            # QA ID 생성
            qa_id = self.generate_qa_id()
            
            # 질문을 임베딩으로 변환
            question_embedding = get_text_embedding(question)
            
            # 메타데이터 구성
            metadata = {
                "question": question,
                "answer": answer,
                "category": category or "general",
                "tags": tags or [],
                "created_at": datetime.now().isoformat(),
                "type": "qa"  # 다른 데이터와 구분하기 위한 타입
            }
            
            # Pinecone에 저장
            self.index.upsert(
                vectors=[{
                    "id": qa_id,
                    "values": question_embedding,
                    "metadata": metadata
                }]
            )
            
            logger.info(f"QA 저장 완료: {qa_id}")
            return qa_id
            
        except Exception as e:
            logger.error(f"QA 저장 실패: {str(e)}")
            raise
    
    def search_qa(
        self, 
        question: str, 
        top_k: int = 3,
        similarity_threshold: float = 0.7,
        category_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """유사한 질문-답변 검색"""
        try:
            # 질문을 임베딩으로 변환
            question_embedding = get_text_embedding(question)
            
            # 필터 조건 구성
            filter_condition = {"type": {"$eq": "qa"}}
            if category_filter:
                filter_condition["category"] = {"$eq": category_filter}
            
            # Pinecone 검색
            search_results = self.index.query(
                vector=question_embedding,
                top_k=top_k,
                include_metadata=True,
                filter=filter_condition
            )
            
            # 결과 필터링 및 포맷팅
            filtered_results = []
            for match in search_results.matches:
                if match.score >= similarity_threshold:
                    result = {
                        "qa_id": match.id,
                        "question": match.metadata.get("question", ""),
                        "answer": match.metadata.get("answer", ""),
                        "similarity_score": round(match.score, 4),
                        "category": match.metadata.get("category"),
                        "tags": match.metadata.get("tags", []),
                        "created_at": match.metadata.get("created_at")
                    }
                    filtered_results.append(result)
            
            logger.info(f"QA 검색 완료: {len(filtered_results)}개 결과")
            return filtered_results
            
        except Exception as e:
            logger.error(f"QA 검색 실패: {str(e)}")
            raise
    
    def get_qa_by_id(self, qa_id: str) -> Optional[Dict[str, Any]]:
        """특정 QA ID로 조회"""
        try:
            fetch_result = self.index.fetch(ids=[qa_id])
            
            if qa_id in fetch_result.vectors:
                vector_data = fetch_result.vectors[qa_id]
                metadata = vector_data.metadata
                
                return {
                    "qa_id": qa_id,
                    "question": metadata.get("question", ""),
                    "answer": metadata.get("answer", ""),
                    "category": metadata.get("category"),
                    "tags": metadata.get("tags", []),
                    "created_at": metadata.get("created_at")
                }
            
            return None
            
        except Exception as e:
            logger.error(f"QA 조회 실패: {str(e)}")
            raise
    
    def delete_qa(self, qa_id: str) -> bool:
        """특정 QA 삭제"""
        try:
            self.index.delete(ids=[qa_id])
            logger.info(f"QA 삭제 완료: {qa_id}")
            return True
            
        except Exception as e:
            logger.error(f"QA 삭제 실패: {str(e)}")
            raise
    
    def list_qa(self, limit: int = 100) -> List[Dict[str, Any]]:
        """저장된 QA 목록 조회"""
        try:
            # Pinecone의 describe_index_stats로 개수 확인
            stats = self.index.describe_index_stats()
            
            # 실제로는 모든 QA를 가져오기 위해 더미 벡터로 검색
            # 주의: 이 방법은 대량 데이터에는 적합하지 않음
            dummy_embedding = [0.0] * 1536  # text-embedding-3-small의 차원
            
            search_results = self.index.query(
                vector=dummy_embedding,
                top_k=min(limit, 10000),  # Pinecone 제한
                include_metadata=True,
                filter={"type": {"$eq": "qa"}}
            )
            
            results = []
            for match in search_results.matches:
                result = {
                    "qa_id": match.id,
                    "question": match.metadata.get("question", ""),
                    "answer": match.metadata.get("answer", ""),
                    "category": match.metadata.get("category"),
                    "tags": match.metadata.get("tags", []),
                    "created_at": match.metadata.get("created_at"),
                    "similarity_score": 0.0  # 더미 검색이므로 의미 없음
                }
                results.append(result)
            
            # 생성일시 기준 정렬
            results.sort(key=lambda x: x.get("created_at", ""), reverse=True)
            
            logger.info(f"QA 목록 조회 완료: {len(results)}개")
            return results
            
        except Exception as e:
            logger.error(f"QA 목록 조회 실패: {str(e)}")
            raise


# 글로벌 인스턴스
qa_vector_store = QAVectorStore()
