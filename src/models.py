"""
API 요청/응답 모델 정의
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class ReviewRequest(BaseModel):
    """리뷰 분석 요청 모델"""
    review_text: str = Field(..., description="분석할 리뷰 텍스트")
    restaurant_name: Optional[str] = Field(None, description="레스토랑 이름")
    restaurant_id: Optional[str] = Field(None, description="레스토랑 ID")


class ReviewListRequest(BaseModel):
    """리뷰 리스트 분석 요청 모델"""
    reviews: List[str] = Field(..., description="분석할 리뷰 텍스트 리스트")
    restaurant_name: str = Field(..., description="레스토랑 이름")
    restaurant_id: str = Field(..., description="레스토랑 ID")
    score_threshold: Optional[float] = Field(0.8, description="확신도 기준값")
    llm_keywords: Optional[List[str]] = Field(None, description="LLM 재분류 키워드")


class SentimentResponse(BaseModel):
    """감성 분석 응답 모델"""
    restaurant_name: str
    restaurant_id: str
    positive_count: int
    negative_count: int
    total_count: int
    positive_ratio: int = Field(..., description="긍정 비율 (%) - 정수값")
    negative_ratio: int = Field(..., description="부정 비율 (%) - 정수값")
    llm_reclassified_count: int


class SimilarReviewRequest(BaseModel):
    """유사 리뷰 검색 요청 모델"""
    query_text: str = Field(..., description="검색 쿼리 텍스트")
    restaurant_id: Optional[str] = Field(None, description="레스토랑 ID 필터")
    limit: int = Field(3, ge=1, le=100, description="반환할 최대 개수")
    min_score: float = Field(0.0, ge=0.0, le=1.0, description="최소 유사도 점수")


class SimilarReviewResponse(BaseModel):
    """유사 리뷰 검색 응답 모델"""
    results: List[Dict[str, Any]] = Field(..., description="검색 결과 리스트")
    total: int = Field(..., description="총 결과 개수")


class SummarizeRequest(BaseModel):
    """리뷰 요약 요청 모델 (벡터 검색 활용)"""
    restaurant_id: str = Field(..., description="레스토랑 ID")
    positive_query: Optional[str] = Field("맛있다 좋다 만족", description="긍정 리뷰 검색 쿼리")
    negative_query: Optional[str] = Field("맛없다 별로 불만", description="부정 리뷰 검색 쿼리")
    limit: int = Field(10, ge=1, le=100, description="각 카테고리당 검색할 최대 리뷰 수")
    min_score: float = Field(0.0, ge=0.0, le=1.0, description="최소 유사도 점수")


class SummarizeResponse(BaseModel):
    """리뷰 요약 응답 모델 (메타데이터 포함)"""
    restaurant_id: str
    positive_summary: str
    negative_summary: str
    overall_summary: str
    positive_reviews: List[Dict[str, Any]] = Field(..., description="긍정 리뷰 메타데이터")
    negative_reviews: List[Dict[str, Any]] = Field(..., description="부정 리뷰 메타데이터")
    positive_count: int
    negative_count: int


class ExtractStrengthsRequest(BaseModel):
    """강점 추출 요청 모델 (벡터 검색 활용)"""
    target_restaurant_id: str = Field(..., description="타겟 레스토랑 ID")
    comparison_restaurant_ids: Optional[List[str]] = Field(None, description="비교 대상 레스토랑 ID 리스트 (None이면 타겟 제외한 모든 레스토랑과 자동 비교)")
    query: Optional[str] = Field("맛있다 좋다 만족", description="긍정 리뷰 검색 쿼리")
    limit: int = Field(5, ge=1, le=50, description="각 레스토랑당 검색할 최대 리뷰 수")
    min_score: float = Field(0.0, ge=0.0, le=1.0, description="최소 유사도 점수")


class ExtractStrengthsResponse(BaseModel):
    """강점 추출 응답 모델 (메타데이터 포함)"""
    target_restaurant_id: str
    strength_summary: str
    target_reviews: List[Dict[str, Any]] = Field(..., description="타겟 레스토랑 긍정 리뷰 메타데이터")
    comparison_reviews: List[Dict[str, Any]] = Field(..., description="비교 대상 레스토랑 긍정 리뷰 메타데이터")
    target_count: int
    comparison_count: int


class RestaurantReviewsResponse(BaseModel):
    """레스토랑 리뷰 조회 응답 모델"""
    restaurant_id: str
    reviews: List[Dict[str, Any]]
    total: int


class UploadDataRequest(BaseModel):
    """벡터 데이터 업로드 요청 모델"""
    data: Dict[str, Any] = Field(..., description="레스토랑 데이터 딕셔너리")


class UploadDataResponse(BaseModel):
    """벡터 데이터 업로드 응답 모델"""
    message: str
    points_count: int
    collection_name: str


class HealthResponse(BaseModel):
    """헬스 체크 응답 모델"""
    status: str
    version: str


class UpsertReviewRequest(BaseModel):
    """리뷰 Upsert 요청 모델"""
    restaurant_id: str = Field(..., description="레스토랑 ID")
    restaurant_name: str = Field(..., description="레스토랑 이름")
    review: Dict[str, Any] = Field(..., description="리뷰 딕셔너리 (review_id, review, user_id, datetime, group, images, version 등)")
    update_version: Optional[int] = Field(None, description="업데이트할 버전 (None이면 항상 업데이트, 지정하면 해당 버전일 때만 업데이트)")


class UpsertReviewResponse(BaseModel):
    """리뷰 Upsert 응답 모델"""
    action: str = Field(..., description="수행된 작업: 'inserted', 'updated', 'skipped'")
    review_id: str = Field(..., description="리뷰 ID")
    version: int = Field(..., description="새로운 버전 번호")
    point_id: str = Field(..., description="Point ID")
    reason: Optional[str] = Field(None, description="skipped인 경우 이유")
    requested_version: Optional[int] = Field(None, description="요청한 버전 (skipped인 경우)")
    current_version: Optional[int] = Field(None, description="현재 버전 (skipped인 경우)")


class UpsertReviewsBatchRequest(BaseModel):
    """리뷰 배치 Upsert 요청 모델"""
    restaurant_id: str = Field(..., description="레스토랑 ID")
    restaurant_name: str = Field(..., description="레스토랑 이름")
    reviews: List[Dict[str, Any]] = Field(..., description="리뷰 딕셔너리 리스트 (review_id, review, user_id, datetime, group, images, version 등)")
    batch_size: Optional[int] = Field(32, ge=1, le=100, description="벡터 인코딩 배치 크기")


class UpsertReviewsBatchResponse(BaseModel):
    """리뷰 배치 Upsert 응답 모델"""
    results: List[Dict[str, Any]] = Field(..., description="각 리뷰의 upsert 결과 리스트")
    total: int = Field(..., description="총 처리된 리뷰 수")
    success_count: int = Field(..., description="성공한 리뷰 수 (inserted + updated)")
    error_count: int = Field(..., description="실패한 리뷰 수")


class DeleteReviewRequest(BaseModel):
    """리뷰 삭제 요청 모델"""
    restaurant_id: str = Field(..., description="레스토랑 ID")
    review_id: str = Field(..., description="리뷰 ID")


class DeleteReviewResponse(BaseModel):
    """리뷰 삭제 응답 모델"""
    action: str = Field(..., description="수행된 작업: 'deleted', 'not_found'")
    review_id: str = Field(..., description="리뷰 ID")
    point_id: str = Field(..., description="Point ID")


class DeleteReviewsBatchRequest(BaseModel):
    """리뷰 배치 삭제 요청 모델"""
    restaurant_id: str = Field(..., description="레스토랑 ID")
    review_ids: List[str] = Field(..., description="리뷰 ID 리스트")


class DeleteReviewsBatchResponse(BaseModel):
    """리뷰 배치 삭제 응답 모델"""
    results: List[Dict[str, Any]] = Field(..., description="각 리뷰의 삭제 결과 리스트")
    total: int = Field(..., description="총 처리된 리뷰 수")
    deleted_count: int = Field(..., description="삭제된 리뷰 수")
    not_found_count: int = Field(..., description="찾을 수 없는 리뷰 수")

