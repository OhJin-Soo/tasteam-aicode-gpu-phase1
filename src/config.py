"""
설정 관리 모듈
"""

import os
from typing import Optional

try:
    import torch
except ImportError:
    torch = None

# 기본 설정값
DEFAULT_SENTIMENT_MODEL = "Dilwolf/Kakao_app-kr_sentiment"
DEFAULT_EMBEDDING_MODEL = "jhgan/ko-sbert-multitask"
DEFAULT_LLM_MODEL = "Qwen/Qwen2.5-7B-Instruct"
DEFAULT_SCORE_THRESHOLD = 0.8
DEFAULT_MAX_RETRIES = 3
DEFAULT_COLLECTION_NAME = "reviews_collection"
DEFAULT_LLM_BATCH_SIZE = 10  # LLM 분류 배치 크기

# LLM 재분류 키워드
DEFAULT_LLM_KEYWORDS = ["는데", "지만"]


class Config:
    """애플리케이션 설정 클래스"""
    
    # 모델 설정
    SENTIMENT_MODEL: str = DEFAULT_SENTIMENT_MODEL
    EMBEDDING_MODEL: str = DEFAULT_EMBEDDING_MODEL
    LLM_MODEL: str = DEFAULT_LLM_MODEL
    
    # 분석 설정
    SCORE_THRESHOLD: float = DEFAULT_SCORE_THRESHOLD
    MAX_RETRIES: int = DEFAULT_MAX_RETRIES
    LLM_KEYWORDS: list = DEFAULT_LLM_KEYWORDS
    LLM_BATCH_SIZE: int = DEFAULT_LLM_BATCH_SIZE
    
    # Qdrant 설정
    COLLECTION_NAME: str = DEFAULT_COLLECTION_NAME
    QDRANT_URL: Optional[str] = os.getenv("QDRANT_URL", ":memory:")
    
    # GPU 설정
    USE_GPU: bool = os.getenv("USE_GPU", "true").lower() == "true"
    GPU_DEVICE: int = int(os.getenv("GPU_DEVICE", "0"))
    USE_FP16: bool = os.getenv("USE_FP16", "true").lower() == "true"
    
    @classmethod
    def get_device(cls):
        """GPU 사용 가능 여부 확인"""
        if torch is None:
            return -1
        if cls.USE_GPU and torch.cuda.is_available():
            return cls.GPU_DEVICE
        return -1
    
    @classmethod
    def get_dtype(cls):
        """양자화 타입 반환"""
        if torch is None:
            return None
        if cls.USE_FP16 and torch.cuda.is_available():
            return torch.float16
        return torch.float32
    
    @classmethod
    def get_optimal_batch_size(cls, model_type: str = "default"):
        """GPU 메모리에 따른 최적 배치 크기 계산"""
        if torch is None or not cls.USE_GPU or not torch.cuda.is_available():
            return 32
        
        try:
            gpu_memory_gb = torch.cuda.get_device_properties(0).total_memory / (1024**3)
        except Exception:
            return 32
        
        if model_type == "llm":
            # LLM은 메모리 사용량이 큼 (7B 모델 기준)
            if gpu_memory_gb >= 40:  # A100
                return 20
            elif gpu_memory_gb >= 24:  # RTX 3090
                return 10
            else:
                return 5
        elif model_type == "sentiment":
            # 감성 분석 모델 (작은 모델)
            if gpu_memory_gb >= 40:
                return 128
            elif gpu_memory_gb >= 24:
                return 64
            else:
                return 32
        else:  # embedding
            # 임베딩 모델
            if gpu_memory_gb >= 40:
                return 128
            elif gpu_memory_gb >= 24:
                return 64
            else:
                return 32
    
    @classmethod
    def validate(cls) -> bool:
        """설정값 검증"""
        # OpenAI API 키 검증 제거 (Qwen 모델 사용)
        return True

