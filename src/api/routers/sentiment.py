"""
감성 분석 라우터
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import List

from ...sentiment_analysis import SentimentAnalyzer
from ...models import ReviewListRequest, SentimentResponse
from ..dependencies import get_sentiment_analyzer

router = APIRouter()


@router.post("/analyze", response_model=SentimentResponse)
async def analyze_sentiment(
    request: ReviewListRequest,
    analyzer: SentimentAnalyzer = Depends(get_sentiment_analyzer),
):
    """
    리뷰 리스트의 감성 분석을 수행하여 positive_ratio와 negative_ratio를 계산합니다.
    
    프로세스:
    1. 인코더 모델(Transformers)로 1차 감성 분석
    2. 확신도가 낮거나 특정 키워드가 포함된 리뷰는 LLM으로 재분류
    3. 최종적으로 positive_ratio, negative_ratio 반환
    
    - **reviews**: 분석할 리뷰 텍스트 리스트
    - **restaurant_name**: 레스토랑 이름
    - **restaurant_id**: 레스토랑 ID
    - **score_threshold**: 확신도 기준값 (기본값: 0.8, 이 값 미만이면 LLM 재분류)
    - **llm_keywords**: LLM 재분류 키워드 (기본값: ["는데", "지만"])
    
    Returns:
        - positive_ratio: 긍정 리뷰 비율 (%)
        - negative_ratio: 부정 리뷰 비율 (%)
        - positive_count: 긍정 리뷰 개수
        - negative_count: 부정 리뷰 개수
    """
    try:
        result = analyzer.analyze(
            review_list=request.reviews,
            restaurant_name=request.restaurant_name,
            restaurant_id=request.restaurant_id,
        )
        return SentimentResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"감성 분석 중 오류 발생: {str(e)}")


@router.post("/analyze/batch", response_model=List[SentimentResponse])
async def analyze_sentiment_batch(
    requests: List[ReviewListRequest],
    analyzer: SentimentAnalyzer = Depends(get_sentiment_analyzer),
):
    """
    여러 레스토랑의 리뷰를 일괄 분석합니다.
    """
    results = []
    for request in requests:
        try:
            result = analyzer.analyze(
                review_list=request.reviews,
                restaurant_name=request.restaurant_name,
                restaurant_id=request.restaurant_id,
            )
            results.append(SentimentResponse(**result))
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"레스토랑 {request.restaurant_name} 분석 중 오류: {str(e)}"
            )
    return results

