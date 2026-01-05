---
name: 7B 모델 기준 RUNPOD GPU 최적화 전략
overview: 현재 사용 중인 Qwen2.5-7B-Instruct 모델을 기준으로, RUNPOD GPU 환경에서의 추론 최적화 전략을 단계별로 수립합니다. INFERENCE_OPTIMIZATION.md의 권장사항을 반영하여 실용적이고 즉시 적용 가능한 최적화 방안을 제시합니다.
todos: []
---

# 7B 모델 기준 RUNPOD GPU 최

적화 전략

## 현재 프로젝트 상태 분석

### 사용 중인 모델

1. **감성 분석**: `Dilwolf/Kakao_app-kr_sentiment` (Transformers Pipeline)
2. **임베딩**: `jhgan/ko-sbert-multitask` (SentenceTransformer)
3. **LLM 추론**: `Qwen/Qwen2.5-7B-Instruct` ✅ (이미 7B 사용 중)

### 현재 최적화 상태

- ✅ **LLM 모델**: 7B 모델 사용 (적절한 크기)
- ✅ **LLM 최적화**: FP16 양자화, device_map="auto" 적용됨
- ⚠️ **SentimentAnalyzer**: GPU 사용 및 FP16 양자화 미적용
- ⚠️ **VectorSearch**: GPU 사용 및 FP16 양자화 미적용
- ⚠️ **동적 배치 크기**: GPU 메모리에 따른 자동 조정 없음
- ⚠️ **캐싱 시스템**: Redis 기반 캐싱 미구현
- ⚠️ **vLLM**: LLM 서빙 프레임워크 미적용

## 모델 적절성 평가

### 1. 감성 분석 모델

**현재**: `Dilwolf/Kakao_app-kr_sentiment`

- ✅ **적절함**: 카카오 앱 리뷰 도메인 특화
- ✅ **검증된 성능**: 한국어 감성 분석에 최적화
- **권장**: 현재 모델 유지, GPU 최적화만 적용

### 2. 임베딩 모델

**현재**: `jhgan/ko-sbert-multitask`

- ✅ **매우 적절함**: 한국어 멀티태스크 SBERT 모델
- ✅ **검증된 성능**: 벡터 차원 768 (적절한 크기)
- **권장**: 현재 모델 유지, GPU 최적화만 적용

### 3. LLM 모델

**현재**: `Qwen/Qwen2.5-7B-Instruct`

- ✅ **매우 적절함**: 
- 짧은 응답 생성 task (50-150 토큰)에 최적
- GPU 메모리: FP16 기준 약 14GB (RTX 3090 24GB에서 여유 있음)
- 성능과 비용의 균형이 우수
- **권장**: 현재 모델 유지, vLLM 및 추가 최적화 적용

## RUNPOD GPU 환경 최적화 전략

### Phase 1: 즉시 적용 (1주 내) - 필수 최적화

#### 1.1 GPU 및 FP16 양자화 적용

**대상 파일**:

- `src/config.py`: GPU 설정 추가
- `src/sentiment_analysis.py`: GPU 및 FP16 적용
- `src/vector_search.py`: GPU 및 FP16 적용

**구현 내용**:

```python
# src/config.py
import os
import torch

class Config:
    # 기존 모델 설정 유지
    SENTIMENT_MODEL: str = DEFAULT_SENTIMENT_MODEL
    EMBEDDING_MODEL: str = DEFAULT_EMBEDDING_MODEL
    LLM_MODEL: str = DEFAULT_LLM_MODEL  # Qwen2.5-7B-Instruct
    
    # GPU 설정 추가
    USE_GPU: bool = os.getenv("USE_GPU", "true").lower() == "true"
    GPU_DEVICE: int = int(os.getenv("GPU_DEVICE", "0"))
    USE_FP16: bool = os.getenv("USE_FP16", "true").lower() == "true"
    
    @classmethod
    def get_device(cls):
        """GPU 사용 가능 여부 확인"""
        if cls.USE_GPU and torch.cuda.is_available():
            return cls.GPU_DEVICE
        return -1
    
    @classmethod
    def get_dtype(cls):
        """양자화 타입 반환"""
        if cls.USE_FP16 and torch.cuda.is_available():
            return torch.float16
        return torch.float32
    
    @classmethod
    def get_optimal_batch_size(cls, model_type: str = "default"):
        """GPU 메모리에 따른 최적 배치 크기 계산"""
        if not cls.USE_GPU or not torch.cuda.is_available():
            return 32
        
        gpu_memory_gb = torch.cuda.get_device_properties(0).total_memory / (1024**3)
        
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
```

**예상 효과**:

- SentimentAnalyzer: 속도 2-5배 향상, 메모리 50% 절감
- VectorSearch: 속도 3-10배 향상, 메모리 50% 절감

#### 1.2 SentimentAnalyzer GPU 최적화

**대상 파일**: `src/sentiment_analysis.py`**구현 내용**:

```python
from .config import Config
import torch

class SentimentAnalyzer:
    def __init__(self, ...):
        device = Config.get_device()
        dtype = Config.get_dtype()
        batch_size = Config.get_optimal_batch_size("sentiment")
        
        self.sentiment = pipeline(
            "sentiment-analysis",
            model=model_name,
            tokenizer=model_name,
            device=device,
            torch_dtype=dtype,  # FP16 양자화
            batch_size=batch_size,
        )
```



#### 1.3 VectorSearch GPU 최적화

**대상 파일**: `src/vector_search.py`**구현 내용**:

```python
from .config import Config
import torch

class VectorSearch:
    def __init__(self, ...):
        self.encoder = SentenceTransformer(Config.EMBEDDING_MODEL)
        
        if Config.USE_GPU and torch.cuda.is_available():
            self.encoder = self.encoder.cuda()
            if Config.USE_FP16:
                self.encoder = self.encoder.half()  # FP16 양자화
            self.batch_size = Config.get_optimal_batch_size("embedding")
        else:
            self.batch_size = 32
```



#### 1.4 LLMUtils 최적화 강화 (7B 모델)

**대상 파일**: `src/llm_utils.py`**현재 상태**: FP16, device_map="auto" 적용됨**추가 최적화**:

- Flash Attention-2 적용 (메모리 효율 및 속도 향상)
- 배치 크기 동적 조정

**구현 내용**:

```python
# Flash Attention-2 설치 필요: pip install flash-attn --no-build-isolation

self.model = AutoModelForCausalLM.from_pretrained(
    model_name,
    torch_dtype=torch.float16 if device != "cpu" else torch.float32,
    device_map="auto",
    attn_implementation="flash_attention_2",  # Flash Attention-2 추가
    trust_remote_code=True,
)

# 배치 크기 동적 조정
self.batch_size = Config.get_optimal_batch_size("llm")
```

**예상 효과**:

- 속도: 1.5-2배 향상 (Flash Attention-2)
- 메모리: 추가 10-20% 절감
- 배치 크기: 2배 증가 가능

### Phase 2: 단기 적용 (2-4주) - 성능 향상

#### 2.1 vLLM 도입 (LLM 서빙 최적화)

**대상 파일**:

- `vllm_server.py`: 새로운 vLLM 서버 생성
- `src/llm_utils.py`: vLLM 옵션 추가

**구현 내용**:

```python
# vllm_server.py
from vllm import LLM, SamplingParams
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# Qwen2.5-7B-Instruct 사용 (현재 모델)
llm = LLM(
    model="Qwen/Qwen2.5-7B-Instruct",
    tensor_parallel_size=1,  # 단일 GPU
    gpu_memory_utilization=0.9,
    max_model_len=4096,
    dtype="float16",  # FP16
    trust_remote_code=True,
)

sampling_params = SamplingParams(
    temperature=0.3,
    top_p=0.95,
    max_tokens=150,  # 짧은 응답에 최적화
)

app = FastAPI()

class GenerateRequest(BaseModel):
    prompt: str
    temperature: float = 0.3
    max_tokens: int = 150

@app.post("/generate")
async def generate(request: GenerateRequest):
    params = SamplingParams(
        temperature=request.temperature,
        max_tokens=request.max_tokens,
    )
    outputs = llm.generate([request.prompt], params)
    return {"text": outputs[0].outputs[0].text}
```

**LLMUtils 통합**:

```python
# src/llm_utils.py에 vLLM 옵션 추가
import requests
from typing import Optional

class LLMUtils:
    def __init__(
        self,
        model_name: str = Config.LLM_MODEL,
        use_vllm: bool = False,
        vllm_url: Optional[str] = None,
        device: Optional[str] = None,
    ):
        self.use_vllm = use_vllm
        if use_vllm:
            self.vllm_url = vllm_url or "http://localhost:8001"
        else:
            # 기존 Transformers 방식
            ...
    
    def _call_vllm(self, prompt: str, temperature: float = 0.3) -> str:
        """vLLM 서버 호출"""
        response = requests.post(
            f"{self.vllm_url}/generate",
            json={"prompt": prompt, "temperature": temperature},
            timeout=30
        )
        return response.json()["text"]
```

**RUNPOD 설정**:

- GPU: RTX 3090 (24GB) 이상 권장
- 메모리 활용률: 0.9
- PagedAttention으로 처리량 향상
- 동시 요청 처리: 10배 이상 증가

**예상 효과**:

- 속도: 5-10배 향상 (기존 Transformers 대비)
- 동시 처리: 10배 이상 증가
- 지연 시간: 50% 감소

#### 2.2 Redis 캐싱 시스템 구축

**대상 파일**:

- `src/cache.py`: 새로운 캐싱 모듈 생성
- `src/llm_utils.py`: 캐싱 통합
- `src/sentiment_analysis.py`: 캐싱 통합
- `src/vector_search.py`: 임베딩 캐싱 통합

**구현 내용**:

```python
# src/cache.py
import redis
import hashlib
import json
from typing import Optional, Any
import logging

logger = logging.getLogger(__name__)

class CacheManager:
    """통합 캐싱 관리자"""
    
    def __init__(self, redis_host='localhost', redis_port=6379, redis_db=0):
        try:
            self.redis = redis.Redis(
                host=redis_host,
                port=redis_port,
                db=redis_db,
                decode_responses=False
            )
            self.redis.ping()
            self.enabled = True
        except Exception as e:
            logger.warning(f"Redis 연결 실패: {e}. 캐싱 비활성화.")
            self.redis = None
            self.enabled = False
    
    def _get_key(self, prefix: str, content: str) -> str:
        """캐시 키 생성"""
        hash_content = hashlib.md5(content.encode()).hexdigest()
        return f"{prefix}:{hash_content}"
    
    def get(self, prefix: str, content: str) -> Optional[Any]:
        """캐시 조회"""
        if not self.enabled:
            return None
        try:
            key = self._get_key(prefix, content)
            cached = self.redis.get(key)
            if cached:
                return json.loads(cached)
        except Exception as e:
            logger.error(f"캐시 조회 실패: {e}")
        return None
    
    def set(self, prefix: str, content: str, value: Any, ttl: int = 3600):
        """캐시 저장"""
        if not self.enabled:
            return
        try:
            key = self._get_key(prefix, content)
            self.redis.setex(key, ttl, json.dumps(value))
        except Exception as e:
            logger.error(f"캐시 저장 실패: {e}")
```

**캐싱 전략**:

- LLM 응답 캐싱: TTL 1시간
- 감성 분석 결과 캐싱: TTL 24시간
- 임베딩 벡터 캐싱: TTL 24시간

**예상 효과**:

- 반복 요청: 100ms 이하 응답
- API 호출 감소: 30-50%

### Phase 3: 중기 적용 (1-3개월) - 고급 최적화

#### 3.1 TensorRT 최적화 (선택적)

**대상**: SentenceTransformer 임베딩 모델**구현 내용**:

- ONNX 변환
- TensorRT 엔진 생성 (FP16/INT8)
- 배치 크기 고정 최적화

**예상 효과**:

- 속도: 3-10배 추가 향상
- 메모리: 추가 50% 절감

#### 3.2 사전 결과 캐싱 (Pre-computation)

**구현 내용**:

- 인기 레스토랑 감성 분석 결과 사전 계산
- 자주 검색되는 쿼리 결과 캐싱
- 배치 작업 스케줄링 (Cron 또는 Celery)

**예상 효과**:

- 피크 시간 부하: 50-70% 감소
- 응답 시간: 10-100배 단축 (캐시 히트 시)

## RUNPOD 배포 전략

### Docker 이미지 구성

```dockerfile
# 베이스 이미지
FROM pytorch/pytorch:2.1.0-cuda11.8-cudnn8-runtime

# 시스템 의존성
RUN apt-get update && apt-get install -y \
    git \
    && rm -rf /var/lib/apt/lists/*

# Python 의존성
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Flash Attention-2 설치
RUN pip install flash-attn --no-build-isolation

# vLLM 설치 (Phase 2)
RUN pip install vllm

# Redis 클라이언트 (Phase 2)
RUN pip install redis

# 모델 다운로드 (선택적, 네트워크 스토리지 활용)
# RUN python -m download_models.py

# 애플리케이션 실행
CMD ["python", "app.py"]
```



### 환경 변수 설정

```bash
# 모델 설정 (현재 모델 유지)
LLM_MODEL=Qwen/Qwen2.5-7B-Instruct
SENTIMENT_MODEL=Dilwolf/Kakao_app-kr_sentiment
EMBEDDING_MODEL=jhgan/ko-sbert-multitask

# GPU 설정
USE_GPU=true
GPU_DEVICE=0
USE_FP16=true

# 모델 캐시 경로 (RUNPOD 네트워크 스토리지)
MODEL_CACHE_PATH=/workspace/models
HF_HOME=/workspace/models

# Redis 설정 (Phase 2)
REDIS_HOST=localhost
REDIS_PORT=6379

# vLLM 설정 (Phase 2)
VLLM_ENABLED=false  # Phase 1에서는 false, Phase 2에서 true
VLLM_PORT=8001
```



### RUNPOD Pod 설정 권장사항

#### 최소 사양 (Phase 1)

- **GPU**: RTX 3090 (24GB)
- 7B 모델 FP16: 약 14GB
- Sentiment + Embedding: 약 2GB
- 여유 메모리: 약 8GB
- **RAM**: 32GB
- **스토리지**: 100GB (네트워크 스토리지)
- **예상 비용**: $0.29/시간

#### 권장 사양 (Phase 2+)

- **GPU**: A100 (40GB)
- vLLM 사용 시 더 큰 배치 크기 가능
- 동시 처리량 증가
- **RAM**: 64GB
- **스토리지**: 200GB (네트워크 스토리지)
- **예상 비용**: $1.10/시간

#### 최적 사양 (고성능)

- **GPU**: A100 (80GB) 또는 H100 (80GB)
- 최대 성능 및 처리량
- **RAM**: 128GB
- **스토리지**: 500GB (네트워크 스토리지)
- **예상 비용**: $2.20/시간 (A100 80GB)

## 성능 모니터링

### 메트릭 수집

- GPU 사용률 (nvidia-smi)
- GPU 메모리 사용량
- 배치 처리 시간
- 캐시 히트율
- API 응답 시간 (P50, P95, P99)

### 로깅 예시

```python
import time
import torch

# 각 단계별 처리 시간 기록
start_time = time.time()
result = sentiment_analyzer.analyze(...)
elapsed_time = time.time() - start_time

logger.info(f"Sentiment analysis: {elapsed_time:.2f}s")
logger.info(f"GPU memory: {torch.cuda.memory_allocated()/1024**3:.2f}GB / {torch.cuda.max_memory_allocated()/1024**3:.2f}GB")
```



## 예상 최종 성능

### Phase 1 적용 후 (7B 모델 기준)

- **속도**: 2-5배 향상
- SentimentAnalyzer: 2-5배
- VectorSearch: 3-10배
- LLMUtils: 1.5-2배 (Flash Attention-2)
- **메모리**: 50% 절감 (FP16)
- **처리량**: 2-3배 증가 (동적 배치 크기)

### Phase 2 적용 후

- **속도**: 10-20배 향상
- vLLM: 5-10배 추가 향상
- 캐싱: 반복 요청 100ms 이하
- **동시 처리**: 10배 이상 증가
- **응답 시간**: 50% 감소

### Phase 3 적용 후

- **속도**: 20-50배 향상
- **응답 시간**: 100ms 이하 (캐시 히트 시)
- **비용**: 85-95% 절감 (캐싱 효과)

## 리스크 및 대응 방안

### 1. GPU 메모리 부족

- **대응**: 
- 동적 배치 크기 자동 조정
- 모델 양자화 강화 (INT8 고려)
- 모델 offloading (CPU로 일부 이동)
- **모니터링**: 실시간 GPU 메모리 모니터링

### 2. Flash Attention-2 설치 실패

- **대응**: 
- 설치 실패 시 기본 attention으로 fallback
- Docker 이미지에 사전 설치
- **대안**: PyTorch SDPA 사용

### 3. vLLM 호환성 문제

- **대응**: 
- 기존 Transformers 방식과 병행
- 환경 변수로 전환 가능
- **롤백**: 즉시 기존 방식으로 전환

### 4. RUNPOD 비용 관리

- **대응**: 
- Spot 인스턴스 활용
- 자동 스케일링
- 사용하지 않을 때 Pod 중지
- **최적화**: 캐싱으로 API 호출 감소

## 구현 우선순위

1. **최우선 (즉시)**: 

- GPU + FP16 양자화 적용 (SentimentAnalyzer, VectorSearch)
- Flash Attention-2 적용 (LLMUtils)
- 동적 배치 크기 조정

2. **높은 우선순위 (단기)**: 

- vLLM 도입
- Redis 캐싱

3. **중간 우선순위 (중기)**: 

- TensorRT 최적화
- 사전 결과 캐싱

4. **낮은 우선순위 (장기)**: 

- QLoRA 파인튜닝 (데이터셋 확보 후)

## 7B 모델의 장점

### 메모리 효율성

- FP16 기준 약 14GB (RTX 3090 24GB에서 여유 있음)
- 더 큰 배치 크기 가능
- 여러 모델 동시 로딩 가능

### 성능

- 짧은 응답 생성 (50-150 토큰)에 최적
- 7B와 14B 성능 차이 미미 (현재 task 기준)
- 더 빠른 추론 속도

### 비용

- 작은 GPU로도 실행 가능