# RUNPOD Serverless 배포 가이드

RUNPOD Serverless Endpoint를 사용하여 API를 배포하는 방법입니다.

## 파일 구조

- `dockerfile.serverless`: RUNPOD serverless용 Dockerfile
- `handler.py`: RUNPOD serverless handler 함수
- `runpod_serverless_test.py`: Serverless endpoint 테스트 스크립트

## Docker 이미지 빌드

```bash
# Serverless용 이미지 빌드
docker build -f dockerfile.serverless -t your-registry/review-api-serverless:latest .

# RUNPOD에 푸시 (또는 RUNPOD에서 직접 빌드)
docker push your-registry/review-api-serverless:latest
```

## RUNPOD Serverless Endpoint 설정

1. **RUNPOD 대시보드에서 Serverless Endpoint 생성**
   - Docker 이미지: `your-registry/review-api-serverless:latest`
   - Handler 파일: `handler.py` (자동으로 인식됨)
   - Handler 함수: `handler` (자동으로 호출됨)

2. **환경 변수 설정** (RUNPOD 대시보드에서)
   ```
   LLM_MODEL=Qwen/Qwen2.5-7B-Instruct
   SENTIMENT_MODEL=Dilwolf/Kakao_app-kr_sentiment
   EMBEDDING_MODEL=jhgan/ko-sbert-multitask
   USE_GPU=true
   GPU_DEVICE=0
   USE_FP16=true
   HF_HOME=/workspace/models
   QDRANT_URL=your-qdrant-url
   PRE_DOWNLOAD_MODELS=true  # 첫 실행 시 모델 다운로드
   ```

3. **GPU 설정**
   - 최소: RTX 3090 (24GB) 또는 동등한 GPU
   - 권장: A100 (40GB) 또는 더 큰 GPU

## Handler 구조

`handler.py`는 다음과 같은 형식의 입력을 받습니다:

```json
{
  "input": {
    "endpoint": "/api/v1/sentiment/analyze",
    "method": "POST",
    "data": {
      "reviews": ["리뷰1", "리뷰2"],
      "restaurant_name": "비즐",
      "restaurant_id": "res_1234"
    }
  }
}
```

응답 형식:

```json
{
  "status": "success",
  "status_code": 200,
  "data": {
    "restaurant_name": "비즐",
    "positive_ratio": 60.0,
    "negative_ratio": 40.0,
    ...
  }
}
```

## 테스트

```bash
# 환경 변수 설정
export RUNPOD_API_KEY='your-api-key'
export RUNPOD_ENDPOINT_ID='your-endpoint-id'

# 테스트 실행
python runpod_serverless_test.py
```

## 지원하는 API 엔드포인트

모든 FastAPI 엔드포인트를 지원합니다:

- `GET /health` - 헬스 체크
- `POST /api/v1/sentiment/analyze` - 감성 분석
- `POST /api/v1/vector/upload` - 벡터 데이터 업로드
- `POST /api/v1/vector/search/similar` - 벡터 검색
- `POST /api/v1/llm/summarize` - 리뷰 요약
- `POST /api/v1/llm/extract/strengths` - 강점 추출
- 기타 모든 API 엔드포인트

## 일반 Pod vs Serverless 차이점

### 일반 Pod (dockerfile)
- FastAPI 서버를 직접 실행 (`app.py`)
- 지속적으로 실행되는 서버
- HTTP 요청을 직접 받음
- `run.sh` 스크립트 사용

### Serverless (dockerfile.serverless)
- Handler 함수를 통해 요청 처리
- 요청이 있을 때만 실행 (Cold start 고려)
- RUNPOD가 자동으로 handler 함수 호출
- `handler.py` 파일 사용

## Cold Start 최적화

RUNPOD serverless는 컨테이너가 재사용되므로, 첫 요청 시 모델 로딩 시간이 걸릴 수 있습니다.

최적화 방법:
1. 모델 사전 다운로드: `PRE_DOWNLOAD_MODELS=true` 설정
2. Handler에서 싱글톤 패턴 사용 (이미 구현됨)
3. 모델을 전역 변수로 로드 (선택적)

## 주의사항

1. **이미지 크기**: 모델을 이미지에 포함하면 크기가 커질 수 있습니다. RUNPOD 네트워크 스토리지를 활용하는 것이 좋습니다.

2. **Cold Start**: 첫 요청 시 모델 로딩으로 인해 응답 시간이 길 수 있습니다.

3. **메모리 관리**: Serverless는 메모리 제한이 있을 수 있으므로, 모델 크기를 고려해야 합니다.

4. **타임아웃**: RUNPOD serverless는 요청 타임아웃이 있을 수 있으므로, 긴 작업은 비동기로 처리하는 것이 좋습니다.

