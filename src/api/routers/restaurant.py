"""
레스토랑 관련 라우터
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import List

from ...review_utils import get_review_list
from ...models import RestaurantReviewsResponse

router = APIRouter()


@router.get("/{restaurant_name}/reviews", response_model=dict)
async def get_reviews_by_name(
    restaurant_name: str,
    data: dict,  # 실제로는 데이터베이스나 스토리지에서 가져와야 함
):
    """
    레스토랑 이름으로 리뷰를 조회합니다.
    
    - **restaurant_name**: 레스토랑 이름
    """
    try:
        review_list, restaurant_id = get_review_list(data, restaurant_name)
        return {
            "restaurant_name": restaurant_name,
            "restaurant_id": restaurant_id,
            "reviews": review_list,
            "total": len(review_list),
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"리뷰 조회 중 오류 발생: {str(e)}")

