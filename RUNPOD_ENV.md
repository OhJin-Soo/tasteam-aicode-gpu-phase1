# 모델 설정
LLM_MODEL=Qwen/Qwen2.5-7B-Instruct
SENTIMENT_MODEL=Dilwolf/Kakao_app-kr_sentiment
EMBEDDING_MODEL=jhgan/ko-sbert-multitask

# GPU 설정
USE_GPU=true
GPU_DEVICE=0
USE_FP16=true

# 모델 다운로드 제어
PRE_DOWNLOAD_MODELS=true  # 첫 실행 시 true, 이후 false

# 모델 캐시 경로 (RunPod 네트워크 스토리지)
MODEL_CACHE_PATH=/workspace/models
HF_HOME=/workspace/models

# Qdrant 설정 (필요시)
QDRANT_URL=your-qdrant-url

# Redis 설정 (Phase 2)
REDIS_HOST=localhost
REDIS_PORT=6379