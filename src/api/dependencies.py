"""
FastAPI 의존성 주입
"""

from functools import lru_cache
from fastapi import Depends
from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient

from ..config import Config
from ..sentiment_analysis import SentimentAnalyzer
from ..vector_search import VectorSearch
from ..llm_utils import LLMUtils


@lru_cache()
def get_encoder() -> SentenceTransformer:
    """SentenceTransformer 인코더 싱글톤"""
    return SentenceTransformer(Config.EMBEDDING_MODEL)


@lru_cache()
def get_qdrant_client() -> QdrantClient:
    """Qdrant 클라이언트 싱글톤"""
    # :memory:는 location 파라미터로 전달해야 함
    if Config.QDRANT_URL == ":memory:":
        return QdrantClient(location=":memory:")
    else:
        return QdrantClient(url=Config.QDRANT_URL)


@lru_cache()
def get_llm_utils() -> LLMUtils:
    """LLM 유틸리티 싱글톤 (Qwen 모델)"""
    return LLMUtils(model_name=Config.LLM_MODEL)


def get_sentiment_analyzer(
    llm_utils: LLMUtils = Depends(get_llm_utils),
) -> SentimentAnalyzer:
    """감성 분석기 의존성"""
    return SentimentAnalyzer(
        llm_utils=llm_utils,
        score_threshold=Config.SCORE_THRESHOLD,
    )


def get_vector_search(
    encoder: SentenceTransformer = Depends(get_encoder),
    qdrant_client: QdrantClient = Depends(get_qdrant_client),
) -> VectorSearch:
    """벡터 검색 의존성"""
    return VectorSearch(
        encoder=encoder,
        qdrant_client=qdrant_client,
        collection_name=Config.COLLECTION_NAME,
    )

