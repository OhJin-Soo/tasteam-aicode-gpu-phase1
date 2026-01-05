"""
벡터 검색 모듈
"""

import uuid
import hashlib
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any

from qdrant_client import QdrantClient, models
from qdrant_client.models import PointStruct
from sentence_transformers import SentenceTransformer
import torch
import numpy as np

from .config import Config
from .review_utils import extract_image_urls, validate_review_data, validate_restaurant_data

logger = logging.getLogger(__name__)


class VectorSearch:
    """벡터 검색 클래스"""
    
    def __init__(
        self,
        encoder: SentenceTransformer,
        qdrant_client: QdrantClient,
        collection_name: str = Config.COLLECTION_NAME,
    ):
        """
        Args:
            encoder: SentenceTransformer 인코더
            qdrant_client: Qdrant 클라이언트
            collection_name: 컬렉션 이름
        """
        self.encoder = encoder
        
        # GPU 및 FP16 최적화 적용
        if Config.USE_GPU and torch.cuda.is_available():
            self.encoder = self.encoder.cuda()
            if Config.USE_FP16:
                self.encoder = self.encoder.half()  # FP16 양자화
            self.batch_size = Config.get_optimal_batch_size("embedding")
        else:
            self.batch_size = 32
        
        self.client = qdrant_client
        self.collection_name = collection_name
        
        # 컬렉션이 없으면 생성
        try:
            self.client.get_collection(collection_name)
        except Exception:
            # 컬렉션이 없으면 생성
            self.client.create_collection(
                collection_name=collection_name,
                vectors_config=models.VectorParams(
                    size=encoder.get_sentence_embedding_dimension(),
                    distance=models.Distance.COSINE,
                ),
            )
    
    def _get_point_id(self, restaurant_id: str, review_id: str) -> str:
        """
        리뷰 ID 기반 Point ID 생성 (일관성 보장)
        
        Args:
            restaurant_id: 레스토랑 ID
            review_id: 리뷰 ID
            
        Returns:
            Point ID (MD5 해시)
        """
        content = f"{restaurant_id}:{review_id}"
        return hashlib.md5(content.encode()).hexdigest()
    
    def prepare_points(self, data: Dict, batch_size: Optional[int] = None) -> List[PointStruct]:
        """
        레스토랑 데이터를 Qdrant 포인트로 변환합니다. (대용량 처리 최적화)
        
        Args:
            data: 레스토랑 데이터 딕셔너리
            batch_size: 배치 인코딩 크기 (None이면 자동으로 최적 크기 사용)
            
        Returns:
            Qdrant PointStruct 리스트
        """
        if batch_size is None:
            batch_size = self.batch_size
        
        points = []
        review_texts = []
        review_metadata = []
        
        # 1단계: 모든 리뷰 텍스트와 메타데이터 수집
        for restaurant in data.get("restaurants", []):
            if not validate_restaurant_data(restaurant):
                logger.warning(f"레스토랑 정보가 불완전합니다: {restaurant}")
                continue
            
            restaurant_id = restaurant.get("restaurant_id")
            restaurant_name = restaurant.get("restaurant_name")
            
            for review in restaurant.get("reviews", []):
                if not validate_review_data(review):
                    logger.warning(f"리뷰 정보가 불완전합니다: {review}")
                    continue
                    
                review_text = review["review"]
                review_texts.append(review_text)
                review_metadata.append({
                    "restaurant_id": restaurant_id,
                    "restaurant_name": restaurant_name,
                    "review_id": review.get("review_id"),
                    "user_id": review.get("user_id"),
                    "datetime": review.get("datetime"),
                    "group": review.get("group"),
                    "review": review_text,
                    "image_urls": extract_image_urls(review.get("images")),
                    "version": review.get("version", 1),  # Version 필드 추가
                    "created_at": review.get("created_at", datetime.now().isoformat()),
                    "updated_at": review.get("updated_at", datetime.now().isoformat()),
                })
        
        # 2단계: 배치로 벡터 인코딩 (대용량 처리 최적화)
        logger.info(f"총 {len(review_texts)}개의 리뷰를 배치로 인코딩합니다 (배치 크기: {batch_size})")
        
        for i in range(0, len(review_texts), batch_size):
            batch_texts = review_texts[i:i + batch_size]
            batch_metadata = review_metadata[i:i + batch_size]
            
            try:
                # 배치 인코딩 (한 번에 처리하여 성능 향상)
                batch_vectors = self.encoder.encode(batch_texts)
                
                for text, vector, metadata in zip(batch_texts, batch_vectors, batch_metadata):
                    try:
                        # review_id 기반 Point ID 생성
                        point_id = self._get_point_id(
                            metadata.get("restaurant_id", ""),
                            metadata.get("review_id", "")
                        )
                        point = PointStruct(
                            id=point_id,
                            vector=vector.tolist(),
                            payload=metadata
                        )
                        points.append(point)
                    except Exception as e:
                        logger.error(f"포인트 생성 중 오류: {metadata.get('review_id')} | {str(e)}")
                        continue
            except Exception as e:
                logger.error(f"배치 인코딩 중 오류 발생 (배치 {i//batch_size + 1}): {str(e)}")
                # 배치 실패 시 개별 처리
                for text, metadata in zip(batch_texts, batch_metadata):
                    try:
                        vector = self.encoder.encode(text)
                        # review_id 기반 Point ID 생성
                        point_id = self._get_point_id(
                            metadata.get("restaurant_id", ""),
                            metadata.get("review_id", "")
                        )
                        point = PointStruct(
                            id=point_id,
                            vector=vector.tolist(),
                            payload=metadata
                        )
                        points.append(point)
                    except Exception as e2:
                        logger.error(f"개별 인코딩 중 오류: {metadata.get('review_id')} | {str(e2)}")
                        continue
        
        logger.info(f"총 {len(points)}개의 포인트를 생성했습니다.")
        return points
    
    def upload_points(self, points: List[PointStruct]) -> None:
        """
        포인트를 Qdrant에 업로드합니다.
        
        Args:
            points: 업로드할 포인트 리스트
        """
        try:
            self.client.upload_points(
                collection_name=self.collection_name,
                points=points
            )
            logger.info(f"{len(points)}개의 포인트를 업로드했습니다.")
        except Exception as e:
            logger.error(f"포인트 업로드 중 오류: {str(e)}")
            raise
    
    def get_restaurant_reviews(self, restaurant_id: str) -> List[Dict]:
        """
        레스토랑 ID로 리뷰를 조회합니다.
        
        Args:
            restaurant_id: 레스토랑 ID
            
        Returns:
            리뷰 payload 리스트
        """
        try:
            records, _ = self.client.scroll(
                collection_name=self.collection_name,
                scroll_filter=models.Filter(
                    must=[
                        models.FieldCondition(
                            key="restaurant_id",
                            match=models.MatchValue(value=restaurant_id)
                        )
                    ]
                )
            )
            return [r.payload for r in records]
        except Exception as e:
            logger.error(f"리뷰 조회 중 오류: {str(e)}")
            return []
    
    def get_all_restaurant_ids(self) -> List[str]:
        """
        컬렉션에 있는 모든 고유한 레스토랑 ID를 반환합니다.
        
        Returns:
            레스토랑 ID 리스트 (정렬됨)
        """
        try:
            restaurant_ids = set()
            
            # Scroll을 사용하여 모든 포인트 조회
            offset = None
            while True:
                records, next_offset = self.client.scroll(
                    collection_name=self.collection_name,
                    offset=offset,
                    limit=100,  # 한 번에 100개씩 조회
                    with_payload=True,
                    with_vectors=False
                )
                
                for record in records:
                    restaurant_id = record.payload.get("restaurant_id")
                    if restaurant_id:
                        restaurant_ids.add(restaurant_id)
                
                if next_offset is None:
                    break
                offset = next_offset
            
            result = sorted(list(restaurant_ids))
            logger.info(f"총 {len(result)}개의 고유한 레스토랑 ID를 찾았습니다.")
            return result
        except Exception as e:
            logger.error(f"레스토랑 ID 조회 중 오류: {str(e)}")
            return []
    
    def query_similar_reviews(
        self,
        query_text: str,
        restaurant_id: Optional[str] = None,
        limit: int = 3,
        min_score: float = 0.0,
    ) -> List[Dict]:
        """
        의미 기반으로 유사한 리뷰를 검색합니다.
        
        Args:
            query_text: 검색 쿼리 텍스트
            restaurant_id: 필터링할 레스토랑 ID (None이면 전체)
            limit: 반환할 최대 개수
            min_score: 최소 유사도 점수
            
        Returns:
            검색 결과 리스트 (payload와 score 포함)
        """
        try:
            query_vector = self.encoder.encode(query_text).tolist()
            
            filter_conditions = []
            if restaurant_id:
                filter_conditions.append(
                    models.FieldCondition(
                        key="restaurant_id",
                        match=models.MatchValue(value=restaurant_id)
                    )
                )
            
            query_filter = models.Filter(must=filter_conditions) if filter_conditions else None
            
            hits = self.client.query_points(
                collection_name=self.collection_name,
                query=query_vector,
                query_filter=query_filter,
                limit=limit
            ).points
            
            results = []
            for hit in hits:
                if hit.score and hit.score >= min_score:
                    results.append({
                        "payload": hit.payload,
                        "score": hit.score
                    })
            
            return results
        except Exception as e:
            logger.error(f"리뷰 검색 중 오류: {str(e)}")
            return []
    
    def get_reviews_with_images(
        self,
        query_text: str,
        limit: int = 10,
        min_score: float = 0.0,
    ) -> List[Dict]:
        """
        이미지가 있는 리뷰를 검색합니다.
        
        Args:
            query_text: 검색 쿼리 텍스트
            limit: 반환할 최대 개수
            min_score: 최소 유사도 점수
            
        Returns:
            이미지 URL이 있는 리뷰 리스트
        """
        results = self.query_similar_reviews(
            query_text,
            restaurant_id=None,
            limit=limit,
            min_score=min_score,
        )
        
        reviews_with_images = []
        for result in results:
            image_urls = result["payload"].get("image_urls", [])
            if image_urls:  # 이미지가 있는 경우만
                reviews_with_images.append({
                    "payload": result["payload"],
                    "score": result["score"],
                    "image_urls": image_urls
                })
        
        return reviews_with_images
    
    def upsert_review(
        self,
        restaurant_id: str,
        restaurant_name: str,
        review: Dict[str, Any],
        update_version: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        리뷰를 upsert합니다 (있으면 업데이트, 없으면 삽입).
        update_filter를 사용하여 낙관적 잠금(Optimistic Locking)을 지원합니다.
        
        Args:
            restaurant_id: 레스토랑 ID
            restaurant_name: 레스토랑 이름
            review: 리뷰 딕셔너리 (review_id, review, user_id, datetime, group, images, version 등)
            update_version: 업데이트할 버전 (None이면 항상 업데이트, 지정하면 해당 버전일 때만 업데이트)
            
        Returns:
            {
                "action": "inserted" | "updated" | "skipped",
                "review_id": str,
                "version": int,
                "point_id": str,
                "reason": str (skipped인 경우)
            }
        """
        try:
            # 1. 리뷰 검증
            if not validate_review_data(review):
                raise ValueError("리뷰 데이터가 유효하지 않습니다.")
            
            review_id = review.get("review_id")
            if not review_id:
                raise ValueError("review_id가 필요합니다.")
            
            # 2. Point ID 생성 (review_id 기반)
            point_id = self._get_point_id(restaurant_id, review_id)
            
            # 3. 벡터 인코딩
            review_text = review["review"]
            vector = self.encoder.encode(review_text).tolist()
            
            # 4. 현재 버전 확인
            current_version = review.get("version", 1)
            new_version = current_version + 1 if update_version is not None else current_version + 1
            
            # 5. Payload 구성
            payload = {
                "restaurant_id": restaurant_id,
                "restaurant_name": restaurant_name,
                "review_id": review_id,
                "user_id": review.get("user_id"),
                "datetime": review.get("datetime"),
                "group": review.get("group"),
                "review": review_text,
                "image_urls": extract_image_urls(review.get("images")),
                "version": new_version,
                "created_at": review.get("created_at", datetime.now().isoformat()),
                "updated_at": datetime.now().isoformat(),
            }
            
            # 6. Upsert 실행
            point = models.PointStruct(
                id=point_id,
                vector=vector,
                payload=payload
            )
            
            # update_filter 설정 (version 기반 낙관적 잠금)
            update_filter = None
            if update_version is not None:
                # 특정 버전일 때만 업데이트 (낙관적 잠금)
                update_filter = models.Filter(
                    must=[
                        models.FieldCondition(
                            key="version",
                            match=models.MatchValue(value=update_version)
                        ),
                        models.FieldCondition(
                            key="review_id",
                            match=models.MatchValue(value=review_id)
                        ),
                    ]
                )
            
            # Upsert 실행
            self.client.upsert(
                collection_name=self.collection_name,
                points=[point],
                update_filter=update_filter,
            )
            
            # 7. 결과 확인
            # Qdrant는 업데이트/삽입 여부를 직접 반환하지 않으므로
            # 기존 포인트 존재 여부로 판단
            existing = self._check_point_exists(point_id)
            
            if existing and update_version is not None:
                # 기존 포인트의 버전 확인
                existing_point = self._get_point_by_id(point_id)
                if existing_point and existing_point.get("version") != update_version:
                    # 버전이 맞지 않으면 스킵
                    logger.warning(
                        f"리뷰 {review_id}: 버전 불일치 "
                        f"(요청: {update_version}, 실제: {existing_point.get('version')})"
                    )
                    return {
                        "action": "skipped",
                        "reason": "version_mismatch",
                        "review_id": review_id,
                        "requested_version": update_version,
                        "current_version": existing_point.get("version") if existing_point else None,
                        "point_id": point_id
                    }
            
            action = "updated" if existing else "inserted"
            logger.info(f"리뷰 {review_id}: {action} (version {new_version})")
            
            return {
                "action": action,
                "review_id": review_id,
                "version": new_version,
                "point_id": point_id
            }
            
        except Exception as e:
            logger.error(f"리뷰 upsert 중 오류: {str(e)}")
            raise
    
    def _check_point_exists(self, point_id: str) -> bool:
        """
        포인트 존재 여부 확인
        
        Args:
            point_id: Point ID
            
        Returns:
            존재 여부
        """
        try:
            result = self.client.retrieve(
                collection_name=self.collection_name,
                ids=[point_id]
            )
            return len(result) > 0
        except Exception:
            return False
    
    def _get_point_by_id(self, point_id: str) -> Optional[Dict[str, Any]]:
        """
        Point ID로 포인트 조회
        
        Args:
            point_id: Point ID
            
        Returns:
            Payload 딕셔너리 (없으면 None)
        """
        try:
            result = self.client.retrieve(
                collection_name=self.collection_name,
                ids=[point_id]
            )
            if result:
                return result[0].payload
            return None
        except Exception:
            return None
    
    def delete_review(
        self,
        restaurant_id: str,
        review_id: str,
    ) -> Dict[str, Any]:
        """
        리뷰를 삭제합니다.
        
        Args:
            restaurant_id: 레스토랑 ID
            review_id: 리뷰 ID
            
        Returns:
            {
                "action": "deleted" | "not_found",
                "review_id": str,
                "point_id": str
            }
        """
        try:
            # Point ID 생성
            point_id = self._get_point_id(restaurant_id, review_id)
            
            # 포인트 존재 여부 확인
            if not self._check_point_exists(point_id):
                logger.warning(f"리뷰 {review_id}를 찾을 수 없습니다 (point_id: {point_id})")
                return {
                    "action": "not_found",
                    "review_id": review_id,
                    "point_id": point_id
                }
            
            # 삭제 실행
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=models.PointIdsList(
                    points=[point_id]
                )
            )
            
            logger.info(f"리뷰 {review_id} 삭제 완료 (point_id: {point_id})")
            
            return {
                "action": "deleted",
                "review_id": review_id,
                "point_id": point_id
            }
            
        except Exception as e:
            logger.error(f"리뷰 삭제 중 오류: {str(e)}")
            raise
    
    def delete_reviews_batch(
        self,
        restaurant_id: str,
        review_ids: List[str],
    ) -> Dict[str, Any]:
        """
        여러 리뷰를 배치로 삭제합니다.
        
        Args:
            restaurant_id: 레스토랑 ID
            review_ids: 리뷰 ID 리스트
            
        Returns:
            {
                "results": [
                    {
                        "action": "deleted" | "not_found",
                        "review_id": str,
                        "point_id": str
                    },
                    ...
                ],
                "total": int,
                "deleted_count": int,
                "not_found_count": int
            }
        """
        if not review_ids:
            return {
                "results": [],
                "total": 0,
                "deleted_count": 0,
                "not_found_count": 0
            }
        
        try:
            # Point ID 리스트 생성
            point_ids = []
            review_id_to_point_id = {}
            
            for review_id in review_ids:
                point_id = self._get_point_id(restaurant_id, review_id)
                point_ids.append(point_id)
                review_id_to_point_id[review_id] = point_id
            
            # 존재 여부 확인
            existing_points = {}
            try:
                retrieved = self.client.retrieve(
                    collection_name=self.collection_name,
                    ids=point_ids
                )
                for point in retrieved:
                    existing_points[point.id] = point.payload
            except Exception as e:
                logger.warning(f"포인트 존재 여부 확인 중 오류: {str(e)}")
            
            # 존재하는 포인트만 삭제
            existing_point_ids = [pid for pid in point_ids if pid in existing_points]
            
            if existing_point_ids:
                # 배치 삭제 실행
                self.client.delete(
                    collection_name=self.collection_name,
                    points_selector=models.PointIdsList(
                        points=existing_point_ids
                    )
                )
                logger.info(f"총 {len(existing_point_ids)}개의 리뷰를 삭제했습니다.")
            
            # 결과 구성
            results = []
            for review_id in review_ids:
                point_id = review_id_to_point_id[review_id]
                if point_id in existing_points:
                    results.append({
                        "action": "deleted",
                        "review_id": review_id,
                        "point_id": point_id
                    })
                else:
                    results.append({
                        "action": "not_found",
                        "review_id": review_id,
                        "point_id": point_id
                    })
            
            deleted_count = sum(1 for r in results if r["action"] == "deleted")
            not_found_count = sum(1 for r in results if r["action"] == "not_found")
            
            logger.info(f"✅ 배치 삭제 완료: {deleted_count}개 삭제, {not_found_count}개 미발견")
            
            return {
                "results": results,
                "total": len(results),
                "deleted_count": deleted_count,
                "not_found_count": not_found_count
            }
            
        except Exception as e:
            logger.error(f"배치 삭제 중 오류: {str(e)}")
            raise
    
    def upsert_reviews_batch(
        self,
        restaurant_id: str,
        restaurant_name: str,
        reviews: List[Dict[str, Any]],
        batch_size: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        여러 리뷰를 배치로 upsert합니다. (성능 최적화)
        
        배치 처리로 벡터 인코딩과 Qdrant upsert를 효율적으로 수행합니다.
        단, update_filter는 지원하지 않습니다 (중복 방지만 가능).
        
        Args:
            restaurant_id: 레스토랑 ID
            restaurant_name: 레스토랑 이름
            reviews: 리뷰 딕셔너리 리스트 (review_id, review, user_id, datetime, group, images, version 등)
            batch_size: 벡터 인코딩 배치 크기 (None이면 자동으로 최적 크기 사용)
            
        Returns:
            각 리뷰의 upsert 결과 리스트:
            [
                {
                    "action": "inserted" | "updated",
                    "review_id": str,
                    "version": int,
                    "point_id": str
                },
                ...
            ]
        """
        if not reviews:
            return []
        
        if batch_size is None:
            batch_size = self.batch_size
        
        results = []
        all_points = []
        point_id_to_review = {}  # point_id -> review 매핑
        
        try:
            # 1. 리뷰 검증 및 텍스트 추출
            review_texts = []
            valid_reviews = []
            
            for review in reviews:
                if not validate_review_data(review):
                    logger.warning(f"리뷰 데이터가 유효하지 않습니다: {review.get('review_id')}")
                    results.append({
                        "action": "error",
                        "review_id": review.get("review_id", "unknown"),
                        "error": "리뷰 데이터가 유효하지 않습니다."
                    })
                    continue
                
                review_id = review.get("review_id")
                if not review_id:
                    logger.warning("review_id가 없는 리뷰를 건너뜁니다.")
                    results.append({
                        "action": "error",
                        "review_id": "unknown",
                        "error": "review_id가 필요합니다."
                    })
                    continue
                
                review_texts.append(review["review"])
                valid_reviews.append(review)
            
            if not valid_reviews:
                return results
            
            # 2. 배치로 벡터 인코딩 (성능 최적화)
            logger.info(f"총 {len(valid_reviews)}개의 리뷰를 배치로 인코딩합니다 (배치 크기: {batch_size})")
            
            all_vectors = []
            for i in range(0, len(review_texts), batch_size):
                batch_texts = review_texts[i:i + batch_size]
                try:
                    batch_vectors = self.encoder.encode(batch_texts)
                    all_vectors.extend(batch_vectors)
                except Exception as e:
                    logger.error(f"배치 인코딩 중 오류 발생 (배치 {i//batch_size + 1}): {str(e)}")
                    # 배치 실패 시 개별 처리
                    for text in batch_texts:
                        try:
                            vector = self.encoder.encode(text)
                            all_vectors.append(vector)
                        except Exception as e2:
                            logger.error(f"개별 인코딩 중 오류: {str(e2)}")
                            all_vectors.append(None)
            
            # 3. 포인트 생성
            for review, vector in zip(valid_reviews, all_vectors):
                if vector is None:
                    results.append({
                        "action": "error",
                        "review_id": review.get("review_id"),
                        "error": "벡터 인코딩 실패"
                    })
                    continue
                
                review_id = review.get("review_id")
                point_id = self._get_point_id(restaurant_id, review_id)
                
                # 버전 관리
                current_version = review.get("version", 1)
                new_version = current_version + 1
                
                # Payload 구성
                payload = {
                    "restaurant_id": restaurant_id,
                    "restaurant_name": restaurant_name,
                    "review_id": review_id,
                    "user_id": review.get("user_id"),
                    "datetime": review.get("datetime"),
                    "group": review.get("group"),
                    "review": review["review"],
                    "image_urls": extract_image_urls(review.get("images")),
                    "version": new_version,
                    "created_at": review.get("created_at", datetime.now().isoformat()),
                    "updated_at": datetime.now().isoformat(),
                }
                
                point = models.PointStruct(
                    id=point_id,
                    vector=vector.tolist(),
                    payload=payload
                )
                
                all_points.append(point)
                point_id_to_review[point_id] = {
                    "review": review,
                    "new_version": new_version
                }
            
            if not all_points:
                return results
            
            # 4. 배치로 upsert (update_filter 없이 - 중복 방지만)
            logger.info(f"총 {len(all_points)}개의 포인트를 배치로 upsert합니다.")
            self.client.upsert(
                collection_name=self.collection_name,
                points=all_points
            )
            
            # 5. 결과 확인 (기존 포인트 존재 여부 확인)
            point_ids = [p.id for p in all_points]
            existing_points = {}
            
            try:
                retrieved = self.client.retrieve(
                    collection_name=self.collection_name,
                    ids=point_ids
                )
                for point in retrieved:
                    existing_points[point.id] = point.payload
            except Exception as e:
                logger.warning(f"기존 포인트 조회 중 오류: {str(e)}")
            
            # 6. 결과 구성
            for point_id in point_ids:
                review_info = point_id_to_review[point_id]
                review_id = review_info["review"]["review_id"]
                new_version = review_info["new_version"]
                
                existing = point_id in existing_points
                action = "updated" if existing else "inserted"
                
                results.append({
                    "action": action,
                    "review_id": review_id,
                    "version": new_version,
                    "point_id": point_id
                })
                
                logger.debug(f"리뷰 {review_id}: {action} (version {new_version})")
            
            logger.info(f"✅ 배치 upsert 완료: {len(results)}개 리뷰 처리")
            return results
            
        except Exception as e:
            logger.error(f"배치 upsert 중 오류: {str(e)}")
            raise


# 편의 함수들
def prepare_qdrant_points(
    data: Dict,
    encoder: SentenceTransformer,
    collection_name: str = Config.COLLECTION_NAME,
) -> List[PointStruct]:
    """
    레스토랑 데이터를 Qdrant 포인트로 변환하는 편의 함수.
    
    Args:
        data: 레스토랑 데이터 딕셔너리
        encoder: SentenceTransformer 인코더
        collection_name: 컬렉션 이름
        
    Returns:
        Qdrant PointStruct 리스트
    """
    # 임시 클라이언트 생성 (실제로는 전달받아야 함)
    from qdrant_client import QdrantClient
    temp_client = QdrantClient(":memory:")
    
    vector_search = VectorSearch(encoder, temp_client, collection_name)
    return vector_search.prepare_points(data)


def get_restaurant_reviews(
    qdrant_client: QdrantClient,
    restaurant_id: str,
    collection_name: str = Config.COLLECTION_NAME,
) -> List[Dict]:
    """
    레스토랑 ID로 리뷰를 조회하는 편의 함수.
    
    Args:
        qdrant_client: Qdrant 클라이언트
        restaurant_id: 레스토랑 ID
        collection_name: 컬렉션 이름
        
    Returns:
        리뷰 payload 리스트
    """
    # encoder는 실제로 필요 없지만 클래스 구조상 필요
    from sentence_transformers import SentenceTransformer
    encoder = SentenceTransformer(Config.EMBEDDING_MODEL)
    
    vector_search = VectorSearch(encoder, qdrant_client, collection_name)
    return vector_search.get_restaurant_reviews(restaurant_id)


def query_similar_reviews(
    qdrant_client: QdrantClient,
    encoder: SentenceTransformer,
    query_text: str,
    restaurant_id: Optional[str] = None,
    collection_name: str = Config.COLLECTION_NAME,
    limit: int = 3,
    min_score: float = 0.0,
) -> List[Dict]:
    """
    의미 기반으로 유사한 리뷰를 검색하는 편의 함수.
    
    Args:
        qdrant_client: Qdrant 클라이언트
        encoder: SentenceTransformer 인코더
        query_text: 검색 쿼리 텍스트
        restaurant_id: 필터링할 레스토랑 ID (None이면 전체)
        collection_name: 컬렉션 이름
        limit: 반환할 최대 개수
        min_score: 최소 유사도 점수
        
    Returns:
        검색 결과 리스트 (payload와 score 포함)
    """
    vector_search = VectorSearch(encoder, qdrant_client, collection_name)
    return vector_search.query_similar_reviews(query_text, restaurant_id, limit, min_score)


def get_reviews_with_images(
    qdrant_client: QdrantClient,
    encoder: SentenceTransformer,
    query_text: str,
    collection_name: str = Config.COLLECTION_NAME,
    limit: int = 10,
    min_score: float = 0.0,
) -> List[Dict]:
    """
    이미지가 있는 리뷰를 검색하는 편의 함수.
    
    Args:
        qdrant_client: Qdrant 클라이언트
        encoder: SentenceTransformer 인코더
        query_text: 검색 쿼리 텍스트
        collection_name: 컬렉션 이름
        limit: 반환할 최대 개수
        min_score: 최소 유사도 점수
        
    Returns:
        이미지 URL이 있는 리뷰 리스트
    """
    vector_search = VectorSearch(encoder, qdrant_client, collection_name)
    return vector_search.get_reviews_with_images(query_text, limit, min_score)

