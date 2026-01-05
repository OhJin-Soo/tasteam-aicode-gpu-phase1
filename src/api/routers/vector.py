"""
벡터 검색 라우터
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import List

from ...vector_search import VectorSearch
from ...models import (
    SimilarReviewRequest,
    SimilarReviewResponse,
    UploadDataRequest,
    UploadDataResponse,
    RestaurantReviewsResponse,
    UpsertReviewRequest,
    UpsertReviewResponse,
    UpsertReviewsBatchRequest,
    UpsertReviewsBatchResponse,
    DeleteReviewRequest,
    DeleteReviewResponse,
    DeleteReviewsBatchRequest,
    DeleteReviewsBatchResponse,
)
from ..dependencies import get_vector_search

router = APIRouter()


@router.post("/search/similar", response_model=SimilarReviewResponse)
async def search_similar_reviews(
    request: SimilarReviewRequest,
    vector_search: VectorSearch = Depends(get_vector_search),
):
    """
    의미 기반 검색(벡터검색)을 통해 유사한 리뷰를 검색합니다.
    
    모든 메타데이터를 포함하여 반환합니다:
    - restaurant_id, restaurant_name
    - review_id, user_id, datetime, group
    - review (리뷰 텍스트)
    - image_urls
    - score (유사도 점수)
    
    - **query_text**: 검색 쿼리 텍스트
    - **restaurant_id**: 레스토랑 ID 필터 (선택사항, None이면 전체 검색)
    - **limit**: 반환할 최대 개수 (기본값: 3, 최대: 100)
    - **min_score**: 최소 유사도 점수 (기본값: 0.0)
    """
    try:
        results = vector_search.query_similar_reviews(
            query_text=request.query_text,
            restaurant_id=request.restaurant_id,
            limit=request.limit,
            min_score=request.min_score,
        )
        return SimilarReviewResponse(results=results, total=len(results))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"벡터 검색 중 오류 발생: {str(e)}")


@router.get("/restaurants/{restaurant_id}/reviews", response_model=RestaurantReviewsResponse)
async def get_restaurant_reviews(
    restaurant_id: str,
    vector_search: VectorSearch = Depends(get_vector_search),
):
    """
    레스토랑 ID로 리뷰를 조회합니다.
    """
    try:
        reviews = vector_search.get_restaurant_reviews(restaurant_id)
        return RestaurantReviewsResponse(
            restaurant_id=restaurant_id,
            reviews=reviews,
            total=len(reviews),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"리뷰 조회 중 오류 발생: {str(e)}")


@router.post("/upload", response_model=UploadDataResponse)
async def upload_vector_data(
    request: UploadDataRequest,
    vector_search: VectorSearch = Depends(get_vector_search),
):
    """
    레스토랑 데이터를 벡터 데이터베이스에 업로드합니다.
    """
    try:
        points = vector_search.prepare_points(request.data)
        vector_search.upload_points(points)
        return UploadDataResponse(
            message="데이터 업로드 완료",
            points_count=len(points),
            collection_name=vector_search.collection_name,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"데이터 업로드 중 오류 발생: {str(e)}")


@router.post("/search/with-images", response_model=SimilarReviewResponse)
async def search_reviews_with_images(
    request: SimilarReviewRequest,
    vector_search: VectorSearch = Depends(get_vector_search),
):
    """
    의미 기반 검색(벡터검색)을 통해 전체 리뷰에서 이미지가 있는 리뷰를 반환합니다.
    
    - **query_text**: 검색 쿼리 텍스트
    - **restaurant_id**: 레스토랑 ID 필터 (선택사항)
    - **limit**: 반환할 최대 개수 (기본값: 3)
    - **min_score**: 최소 유사도 점수 (기본값: 0.0)
    
    Returns:
        이미지가 포함된 리뷰 리스트 (모든 메타데이터 포함)
    """
    try:
        results = vector_search.get_reviews_with_images(
            query_text=request.query_text,
            limit=request.limit,
            min_score=request.min_score,
        )
        return SimilarReviewResponse(results=results, total=len(results))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"이미지 리뷰 검색 중 오류 발생: {str(e)}")


@router.post("/reviews/upsert", response_model=UpsertReviewResponse)
async def upsert_review(
    request: UpsertReviewRequest,
    vector_search: VectorSearch = Depends(get_vector_search),
):
    """
    리뷰를 upsert합니다 (있으면 업데이트, 없으면 삽입).
    update_filter를 사용하여 낙관적 잠금(Optimistic Locking)을 지원합니다.
    
    **동작 방식:**
    1. `update_version`이 None이면: 항상 업데이트/삽입 (중복 방지)
    2. `update_version`이 지정되면: 해당 버전일 때만 업데이트 (낙관적 잠금)
    
    **사용 시나리오:**
    - **리뷰 추가/수정 (중복 방지)**: `update_version=None`
      - 같은 review_id가 있으면 자동으로 업데이트
      - 없으면 새로 삽입
      
    - **리뷰 수정 (동시성 제어)**: `update_version=3`
      - 현재 버전이 3일 때만 업데이트
      - 다른 사용자가 먼저 수정했다면 (version이 4 이상) 스킵
    
    **요청 예시:**
    ```json
    {
        "restaurant_id": "res_1234",
        "restaurant_name": "비즐",
        "review": {
            "review_id": "rev_3001",
            "review": "맛있어요!",
            "user_id": "user_123",
            "datetime": "2024-01-01T12:00:00",
            "group": "group_1",
            "version": 3
        },
        "update_version": 3  // 이 버전일 때만 업데이트
    }
    ```
    
    **응답:**
    - `action`: "inserted" (새로 삽입), "updated" (업데이트), "skipped" (스킵)
    - `version`: 새로운 버전 번호
    - `reason`: skipped인 경우 이유 ("version_mismatch" 등)
    """
    try:
        result = vector_search.upsert_review(
            restaurant_id=request.restaurant_id,
            restaurant_name=request.restaurant_name,
            review=request.review,
            update_version=request.update_version,
        )
        return UpsertReviewResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"리뷰 upsert 중 오류 발생: {str(e)}")


@router.post("/reviews/upsert/batch", response_model=UpsertReviewsBatchResponse)
async def upsert_reviews_batch(
    request: UpsertReviewsBatchRequest,
    vector_search: VectorSearch = Depends(get_vector_search),
):
    """
    여러 리뷰를 배치로 upsert합니다. (성능 최적화)
    
    **특징:**
    - 배치 벡터 인코딩으로 성능 향상
    - 배치 Qdrant upsert로 효율적인 처리
    - 10개 리뷰를 1번의 API 호출로 처리 가능
    
    **제한사항:**
    - `update_filter`는 지원하지 않습니다 (중복 방지만 가능)
    - 낙관적 잠금이 필요한 경우 개별 upsert 엔드포인트 사용
    
    **요청 예시:**
    ```json
    {
        "restaurant_id": "res_1234",
        "restaurant_name": "비즐",
        "reviews": [
            {
                "review_id": "rev_3001",
                "review": "맛있어요!",
                "user_id": "user_123",
                "datetime": "2024-01-01T12:00:00",
                "group": "group_1",
                "version": 1
            },
            {
                "review_id": "rev_3002",
                "review": "좋아요!",
                "user_id": "user_124",
                "datetime": "2024-01-01T12:01:00",
                "group": "group_1",
                "version": 1
            }
        ],
        "batch_size": 32
    }
    ```
    
    **응답:**
    - `results`: 각 리뷰의 upsert 결과 리스트
    - `total`: 총 처리된 리뷰 수
    - `success_count`: 성공한 리뷰 수 (inserted + updated)
    - `error_count`: 실패한 리뷰 수
    """
    try:
        results = vector_search.upsert_reviews_batch(
            restaurant_id=request.restaurant_id,
            restaurant_name=request.restaurant_name,
            reviews=request.reviews,
            batch_size=request.batch_size,
        )
        
        # 통계 계산
        success_count = sum(1 for r in results if r.get("action") in ["inserted", "updated"])
        error_count = sum(1 for r in results if r.get("action") == "error")
        
        return UpsertReviewsBatchResponse(
            results=results,
            total=len(results),
            success_count=success_count,
            error_count=error_count,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"배치 upsert 중 오류 발생: {str(e)}")


@router.delete("/reviews/delete", response_model=DeleteReviewResponse)
async def delete_review(
    request: DeleteReviewRequest,
    vector_search: VectorSearch = Depends(get_vector_search),
):
    """
    리뷰를 삭제합니다.
    
    **동작 방식:**
    - review_id를 기반으로 Point ID를 생성하여 삭제
    - 리뷰가 존재하지 않으면 "not_found" 반환
    
    **요청 예시:**
    ```json
    {
        "restaurant_id": "res_1234",
        "review_id": "rev_3001"
    }
    ```
    
    **응답:**
    - `action`: "deleted" (삭제됨), "not_found" (찾을 수 없음)
    - `review_id`: 리뷰 ID
    - `point_id`: Point ID
    """
    try:
        result = vector_search.delete_review(
            restaurant_id=request.restaurant_id,
            review_id=request.review_id,
        )
        return DeleteReviewResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"리뷰 삭제 중 오류 발생: {str(e)}")


@router.delete("/reviews/delete/batch", response_model=DeleteReviewsBatchResponse)
async def delete_reviews_batch(
    request: DeleteReviewsBatchRequest,
    vector_search: VectorSearch = Depends(get_vector_search),
):
    """
    여러 리뷰를 배치로 삭제합니다.
    
    **특징:**
    - 여러 리뷰를 한 번에 삭제하여 성능 향상
    - 존재하지 않는 리뷰는 자동으로 건너뜀
    
    **요청 예시:**
    ```json
    {
        "restaurant_id": "res_1234",
        "review_ids": ["rev_3001", "rev_3002", "rev_3003"]
    }
    ```
    
    **응답:**
    - `results`: 각 리뷰의 삭제 결과 리스트
    - `total`: 총 처리된 리뷰 수
    - `deleted_count`: 삭제된 리뷰 수
    - `not_found_count`: 찾을 수 없는 리뷰 수
    """
    try:
        result = vector_search.delete_reviews_batch(
            restaurant_id=request.restaurant_id,
            review_ids=request.review_ids,
        )
        return DeleteReviewsBatchResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"배치 삭제 중 오류 발생: {str(e)}")

