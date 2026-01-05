"""
감성 분석 모듈
"""

import json
import logging
from typing import Dict, List, Optional

import torch
from transformers import pipeline

from .config import Config
from .llm_utils import LLMUtils

# 로깅 설정
logger = logging.getLogger(__name__)


class SentimentAnalyzer:
    """
    감성 분석 클래스
    
    인코더 모델(Transformers)과 LLM을 결합하여 리뷰를 분류하고
    positive_ratio와 negative_ratio를 계산합니다.
    
    프로세스:
    1. 인코더 모델(Transformers pipeline)로 1차 감성 분석
    2. 확신도가 낮거나 특정 키워드가 포함된 리뷰는 LLM으로 재분류
    3. 최종적으로 positive_count, negative_count를 집계하여 비율 계산
    """
    
    def __init__(
        self,
        model_name: str = Config.SENTIMENT_MODEL,
        llm_utils: Optional[LLMUtils] = None,
        score_threshold: float = Config.SCORE_THRESHOLD,
        llm_keywords: Optional[List[str]] = None,
    ):
        """
        Args:
            model_name: 감성 분석 인코더 모델명 (Transformers pipeline)
            llm_utils: LLMUtils 인스턴스 (None이면 자동 생성)
            score_threshold: 확신도 기준값 (이 값 미만이면 LLM 재분류)
            llm_keywords: LLM 재분류 대상 키워드 리스트
        """
        # GPU 및 FP16 설정
        device = Config.get_device()
        dtype = Config.get_dtype()
        batch_size = Config.get_optimal_batch_size("sentiment")
        
        # 인코더 모델 초기화 (Transformers pipeline)
        pipeline_kwargs = {
            "model": model_name,
            "tokenizer": model_name,
        }
        
        if device >= 0:
            pipeline_kwargs["device"] = device
        if dtype is not None:
            pipeline_kwargs["torch_dtype"] = dtype
        pipeline_kwargs["batch_size"] = batch_size  # FP16 양자화 및 배치 크기 적용
        
        self.sentiment = pipeline("sentiment-analysis", **pipeline_kwargs)
        
        # 배치 크기 저장 (analyze 메서드에서 사용)
        self.batch_size = batch_size
        self.llm_utils = llm_utils or LLMUtils()
        self.score_threshold = score_threshold
        self.llm_keywords = llm_keywords or Config.LLM_KEYWORDS
    
    def analyze(
        self,
        review_list: List[str],
        restaurant_name: str,
        restaurant_id: str,
        max_retries: int = Config.MAX_RETRIES,
    ) -> Dict:
        """
        리뷰 리스트를 분석하여 positive_ratio와 negative_ratio를 계산합니다.
        
        프로세스:
        1. 인코더 모델로 1차 감성 분석 수행
        2. 확신도가 낮거나 키워드가 포함된 리뷰는 LLM으로 재분류
        3. 최종 집계하여 positive_ratio, negative_ratio 계산
        
        Args:
            review_list: 분석할 리뷰 문자열 리스트
            restaurant_name: 레스토랑 이름
            restaurant_id: 레스토랑 ID
            max_retries: LLM 호출 실패 시 최대 재시도 횟수
            
        Returns:
            최종 통계 결과 딕셔너리:
            - positive_count: 긍정 리뷰 개수
            - negative_count: 부정 리뷰 개수
            - total_count: 전체 리뷰 개수
            - positive_ratio: 긍정 비율 (%)
            - negative_ratio: 부정 비율 (%)
        """
        positive, negative = 0, 0
        llm_input_list = []
        low_confidence_list = []

        # 1️⃣ 인코더 모델로 1차 감성 분석 (배치 처리로 최적화)
        logger.info(f"총 {len(review_list)}개의 리뷰를 분석합니다.")
        
        # 동적 배치 크기 사용
        batch_size = self.batch_size
        
        for i in range(0, len(review_list), batch_size):
            batch = review_list[i:i + batch_size]
            try:
                # 배치로 한 번에 처리 (성능 향상)
                batch_results = self.sentiment(batch)
                
                for text, result in zip(batch, batch_results):
                    label = result["label"]
                    score = result["score"]
                    
                    logger.debug(f"리뷰: {text[:50]}... | 라벨: {label} | 점수: {score:.3f}")

                    # 확신도가 낮거나 키워드가 포함된 경우 LLM 재분류 대상에 추가
                    needs_llm_review = (
                        score < self.score_threshold or  # 확신도 낮음
                        any(kw in text for kw in self.llm_keywords)  # 키워드 포함
                    )
                    
                    if needs_llm_review:
                        if score < self.score_threshold:
                            low_confidence_list.append(text)
                        if any(kw in text for kw in self.llm_keywords):
                            llm_input_list.append(text)
                    else:
                        # 확신도가 높으면 바로 분류
                        if label == "positive":
                            positive += 1
                        elif label == "negative":
                            negative += 1
            except Exception as e:
                logger.error(f"배치 분석 중 오류 발생 (배치 {i//batch_size + 1}): {str(e)}")
                # 배치 실패 시 개별 처리
                for text in batch:
                    try:
                        result = self.sentiment(text)[0]
                        label = result["label"]
                        score = result["score"]
                        
                        needs_llm_review = (
                            score < self.score_threshold or
                            any(kw in text for kw in self.llm_keywords)
                        )
                        
                        if needs_llm_review:
                            if score < self.score_threshold:
                                low_confidence_list.append(text)
                            if any(kw in text for kw in self.llm_keywords):
                                llm_input_list.append(text)
                        else:
                            if label == "positive":
                                positive += 1
                            elif label == "negative":
                                negative += 1
                    except Exception as e2:
                        logger.error(f"리뷰 분석 중 오류 발생: {text[:50]}... | 오류: {str(e2)}")
                        # 오류 발생 시 LLM 재분류 대상에 추가
                        llm_input_list.append(text)

        # 중복 제거
        llm_input_list = list(set(llm_input_list + low_confidence_list))
        
        # 2️⃣ LLM 재분류 (개수 집계 방식 - 효율적)
        if llm_input_list:
            logger.info(f"LLM 재분류 대상: {len(llm_input_list)}개")
            logger.info(f"  - 확신도 낮음: {len(low_confidence_list)}개")
            logger.info(f"  - 키워드 포함: {len([t for t in llm_input_list if any(kw in t for kw in self.llm_keywords)])}개")
            
            # 개선: 모든 리뷰를 한 번에 보내고 개수만 반환받는 방식
            counts = self.llm_utils.count_sentiments(
                llm_input_list, max_retries=max_retries
            )
            
            positive += counts["positive_count"]
            negative += counts["negative_count"]
            
            logger.info(f"LLM 재분류 결과: 긍정 {counts['positive_count']}개, 부정 {counts['negative_count']}개")

        # 3️⃣ 최종 통계 계산: positive_ratio, negative_ratio 산출
        total = positive + negative
        if total == 0:
            logger.warning("분류된 리뷰가 없습니다.")
            positive_ratio = 0
            negative_ratio = 0
        else:
            # 비율 계산 (퍼센트) - int로 반환
            positive_ratio = int(round((positive / total) * 100))
            negative_ratio = int(round((negative / total) * 100))

        final_summary = {
            "restaurant_name": restaurant_name,
            "restaurant_id": restaurant_id,
            "positive_count": positive,
            "negative_count": negative,
            "total_count": total,
            "positive_ratio": positive_ratio,  # 긍정 비율 (%) - int
            "negative_ratio": negative_ratio,  # 부정 비율 (%) - int
            "llm_reclassified_count": len(llm_input_list)
        }

        logger.info("✅ 최종 결과:")
        logger.info(json.dumps(final_summary, ensure_ascii=False, indent=2))

        return final_summary


def analyze_reviews(
    review_list: List[str],
    restaurant_name: str,
    restaurant_id: str,
    llm_utils: Optional[LLMUtils] = None,
    score_threshold: float = Config.SCORE_THRESHOLD,
    llm_keywords: Optional[List[str]] = None,
    max_retries: int = Config.MAX_RETRIES,
) -> Dict:
    """
    리뷰 리스트를 분석하는 편의 함수.
    
    Args:
        review_list: 분석할 리뷰 문자열 리스트
        restaurant_name: 레스토랑 이름
        restaurant_id: 레스토랑 ID
        llm_utils: LLMUtils 인스턴스 (None이면 자동 생성)
        score_threshold: sentiment 확신도 기준
        llm_keywords: LLM 재분류 대상 키워드 리스트
        max_retries: LLM 호출 실패 시 최대 재시도 횟수
        
    Returns:
        최종 통계 결과 딕셔너리
    """
    analyzer = SentimentAnalyzer(
        llm_utils=llm_utils,
        score_threshold=score_threshold,
        llm_keywords=llm_keywords,
    )
    return analyzer.analyze(review_list, restaurant_name, restaurant_id, max_retries)

