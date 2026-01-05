"""
LLM 관련 라우터 (벡터 검색 통합)
"""

import logging
from fastapi import APIRouter, HTTPException, Depends
from typing import List

from ...llm_utils import LLMUtils
from ...vector_search import VectorSearch
from ...models import (
    SummarizeRequest,
    SummarizeResponse,
    ExtractStrengthsRequest,
    ExtractStrengthsResponse,
)
from ..dependencies import get_llm_utils, get_vector_search

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/summarize", response_model=SummarizeResponse)
async def summarize_reviews(
    request: SummarizeRequest,
    llm_utils: LLMUtils = Depends(get_llm_utils),
    vector_search: VectorSearch = Depends(get_vector_search),
):
    """
    벡터 검색을 활용하여 긍정/부정 리뷰를 자동 검색하고 요약합니다.
    
    프로세스:
    1. 벡터 검색으로 긍정 리뷰 자동 검색
    2. 벡터 검색으로 부정 리뷰 자동 검색
    3. 검색된 리뷰를 LLM으로 요약
    4. 메타데이터와 함께 반환
    
    - **restaurant_id**: 레스토랑 ID
    - **positive_query**: 긍정 리뷰 검색 쿼리 (기본값: "맛있다 좋다 만족")
    - **negative_query**: 부정 리뷰 검색 쿼리 (기본값: "맛없다 별로 불만")
    - **limit**: 각 카테고리당 검색할 최대 리뷰 수 (기본값: 10)
    - **min_score**: 최소 유사도 점수 (기본값: 0.0)
    """
    try:
        # 1. 벡터 검색으로 긍정 리뷰 검색
        positive_results = vector_search.query_similar_reviews(
            query_text=request.positive_query,
            restaurant_id=request.restaurant_id,
            limit=request.limit,
            min_score=request.min_score,
        )
        
        # 2. 벡터 검색으로 부정 리뷰 검색
        negative_results = vector_search.query_similar_reviews(
            query_text=request.negative_query,
            restaurant_id=request.restaurant_id,
            limit=request.limit,
            min_score=request.min_score,
        )
        
        # 3. payload 추출 (메타데이터 포함)
        positive_reviews = [r["payload"] for r in positive_results]
        negative_reviews = [r["payload"] for r in negative_results]
        
        if not positive_reviews and not negative_reviews:
            raise HTTPException(
                status_code=404,
                detail=f"레스토랑 {request.restaurant_id}에 대한 리뷰를 찾을 수 없습니다."
            )
        
        # 4. LLM으로 요약
        result = llm_utils.summarize_reviews(
            positive_reviews=positive_reviews,
            negative_reviews=negative_reviews,
        )
        
        # 5. restaurant_id 추가
        result["restaurant_id"] = request.restaurant_id
        
        # 6. 응답 검증 (긍정/부정/전체 요약 모두 포함 확인)
        if not result or not all(key in result for key in ["positive_summary", "negative_summary", "overall_summary"]):
            raise HTTPException(
                status_code=500, 
                detail="리뷰 요약 실패: 긍정/부정/전체 요약이 모두 생성되지 않았습니다."
            )
        
        return SummarizeResponse(**result)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"리뷰 요약 중 오류 발생: {str(e)}")


@router.post("/extract/strengths", response_model=ExtractStrengthsResponse)
async def extract_strengths(
    request: ExtractStrengthsRequest,
    llm_utils: LLMUtils = Depends(get_llm_utils),
    vector_search: VectorSearch = Depends(get_vector_search),
):
    """
    벡터 검색을 활용하여 타겟 레스토랑의 강점을 추출합니다.
    
    프로세스:
    1. 벡터 검색으로 타겟 레스토랑의 긍정 리뷰 검색
    2. 벡터 검색으로 비교 대상 레스토랑들의 긍정 리뷰 검색
    3. 검색된 리뷰를 비교하여 강점 추출
    4. 메타데이터와 함께 반환
    
    - **target_restaurant_id**: 타겟 레스토랑 ID
    - **comparison_restaurant_ids**: 비교 대상 레스토랑 ID 리스트 (None이면 타겟 제외한 모든 레스토랑과 자동 비교)
    - **query**: 긍정 리뷰 검색 쿼리 (기본값: "맛있다 좋다 만족")
    - **limit**: 각 레스토랑당 검색할 최대 리뷰 수 (기본값: 5)
    - **min_score**: 최소 유사도 점수 (기본값: 0.0)
    """
    try:
        # 1. 타겟 레스토랑의 긍정 리뷰 검색
        target_results = vector_search.query_similar_reviews(
            query_text=request.query,
            restaurant_id=request.target_restaurant_id,
            limit=request.limit,
            min_score=request.min_score,
        )
        
        target_reviews = [r["payload"] for r in target_results]
        
        if not target_reviews:
            raise HTTPException(
                status_code=404,
                detail=f"타겟 레스토랑 {request.target_restaurant_id}에 대한 긍정 리뷰를 찾을 수 없습니다."
            )
        
        # 2. 비교 대상 레스토랑들의 긍정 리뷰 검색
        comparison_reviews = []
        
        if request.comparison_restaurant_ids:
            # 특정 레스토랑들과 비교
            for comp_id in request.comparison_restaurant_ids:
                comp_results = vector_search.query_similar_reviews(
                    query_text=request.query,
                    restaurant_id=comp_id,
                    limit=request.limit,
                    min_score=request.min_score,
                )
                comparison_reviews.extend([r["payload"] for r in comp_results])
        else:
            # 전체 레스토랑과 비교 (타겟 제외)
            # 1. 모든 레스토랑 ID 가져오기
            all_restaurant_ids = vector_search.get_all_restaurant_ids()
            
            # 2. 타겟 제외
            comparison_restaurant_ids = [
                rid for rid in all_restaurant_ids 
                if rid != request.target_restaurant_id
            ]
            
            if not comparison_restaurant_ids:
                raise HTTPException(
                    status_code=404,
                    detail="비교할 수 있는 다른 레스토랑이 없습니다."
                )
            
            logger.info(
                f"타겟 제외한 비교 대상 레스토랑: {len(comparison_restaurant_ids)}개"
            )
            
            # 3. 각 레스토랑에 대해 검색
            for comp_id in comparison_restaurant_ids:
                comp_results = vector_search.query_similar_reviews(
                    query_text=request.query,
                    restaurant_id=comp_id,
                    limit=request.limit,
                    min_score=request.min_score,
                )
                comparison_reviews.extend([r["payload"] for r in comp_results])
        
        # 3. LLM으로 강점 추출
        result = llm_utils.extract_strengths(
            target_reviews=target_reviews,
            comparison_reviews=comparison_reviews,
            target_restaurant_id=request.target_restaurant_id,
        )
        
        if not result or "strength_summary" not in result:
            raise HTTPException(status_code=500, detail="강점 추출 실패")
        
        return ExtractStrengthsResponse(**result)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"강점 추출 중 오류 발생: {str(e)}")

