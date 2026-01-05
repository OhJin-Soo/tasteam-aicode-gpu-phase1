# Review Analysis API

레스토랑 리뷰의 감성 분석, 벡터 검색, LLM 기반 요약 및 강점 추출을 수행하는 FastAPI 기반 프로젝트입니다.

**LLM 모델**: Qwen2.5-7B-Instruct (로컬 추론, OpenAI API 불필요)

## 주요 기능

1. **감성 분석** (인코더 모델 + LLM 분류) → `positive_ratio`, `negative_ratio` 추출
2. **리뷰 요약** (벡터 검색 활용) → 긍정/부정/전체 요약 + 메타데이터
3. **강점 추출** (벡터 검색 활용) → 다른 리뷰들과 비교하여 강점 추출 + 메타데이터
4. **리뷰 Upsert** (포인트 업데이트) → 낙관적 잠금을 지원하는 리뷰 추가/수정
   - 개별 upsert: 낙관적 잠금 지원
   - 배치 upsert: 성능 최적화 (10개 리뷰를 1번의 API 호출로 처리)
5. **이미지 리뷰 검색** (벡터 검색) → 의미 기반 검색으로 이미지가 있는 리뷰 반환 + 메타데이터

**모든 응답은 메타데이터를 포함합니다** (restaurant_id, review_id, user_id, datetime, group, image_urls 등)

## 프로젝트 구조

```
tasteam-project-aicode/
├── src/                      # 소스 코드 모듈
│   ├── __init__.py          # 패키지 초기화
│   ├── config.py            # 설정 관리
│   ├── models.py            # Pydantic 모델 정의
│   ├── review_utils.py      # 리뷰 처리 유틸리티
│   ├── sentiment_analysis.py # 감성 분석
│   ├── vector_search.py     # 벡터 검색
│   ├── llm_utils.py         # LLM 유틸리티
│   └── api/                 # FastAPI 애플리케이션
│       ├── main.py          # FastAPI 메인 앱
│       ├── dependencies.py  # 의존성 주입
│       └── routers/         # API 라우터
│           ├── sentiment.py    # 감성 분석 엔드포인트
│           ├── vector.py        # 벡터 검색 엔드포인트
│           ├── llm.py          # LLM 요약/강점 추출 엔드포인트
│           └── restaurant.py   # 레스토랑 관련 엔드포인트
├── test_api.ipynb   # API 테스트 노트북 (예제)
├── app.py                  # FastAPI 서버 실행 스크립트
├── requirements.txt        # 패키지 의존성
├── README.md              # 프로젝트 문서
├── API_USAGE.md           # API 사용 가이드
├── API_SPECIFICATION.md   # API 명세서 (엔드포인트 목록, 스키마, 아키텍처)
└── PROJECT_REVIEW.md      # 프로젝트 점검 보고서
```

## 설치

1. 가상환경 생성 및 활성화:
```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

2. 패키지 설치:
```bash
pip install -r requirements.txt
```

**주의사항:**
- Qwen2.5-14B-Instruct 모델은 약 14GB의 메모리가 필요합니다
- GPU 사용 시 CUDA가 설치되어 있어야 합니다
- 모델 최초 다운로드 시 시간이 걸릴 수 있습니다

3. 환경 변수 설정 (선택사항):
```bash
export QDRANT_URL=":memory:"  # 또는 실제 Qdrant 서버 URL
```

## 사용 방법

### FastAPI 서버 실행

1. 환경 변수 설정 (선택사항):
```bash
export QDRANT_URL=":memory:"  # 또는 실제 Qdrant 서버 URL
```

2. 서버 실행:
```bash
# 방법 1: uvicorn 직접 실행
uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload

# 방법 2: app.py 실행
python app.py
```

3. API 문서 확인:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### ✅ 지원 기능

현재 API는 다음 주요 기능들을 지원합니다:

1. ✅ **리뷰 감성 비율 추출** (인코더 모델 + LLM 분류)
   - `positive_ratio`, `negative_ratio` 계산
   - 대용량 리뷰 배치 처리 지원

2. ✅ **리뷰 요약** (벡터 검색 활용)
   - 긍정/부정/전체 요약 자동 생성
   - 벡터 검색으로 관련 리뷰 자동 검색
   - 모든 메타데이터 포함

3. ✅ **강점 추출** (벡터 검색 활용)
   - 다른 리뷰들과 비교하여 강점 추출
   - 벡터 검색으로 비교 대상 자동 검색
   - 모든 메타데이터 포함

4. ✅ **리뷰 Upsert** (포인트 업데이트)
   - 낙관적 잠금을 지원하는 리뷰 추가/수정/삭제
   - 배치 처리로 성능 최적화

5. ✅ **이미지 리뷰 검색** (벡터 검색)
   - 의미 기반 검색으로 이미지가 있는 리뷰 반환
   - 모든 메타데이터 포함

자세한 사용법은 [API_USAGE.md](API_USAGE.md)를 참고하세요.

**📋 전체 API 명세서**: [API_SPECIFICATION.md](API_SPECIFICATION.md)에서 다음을 확인할 수 있습니다:
- 전체 엔드포인트 목록 및 기능 설명
- 입출력 스키마 명세 (JSON Schema)
- 시스템 아키텍처 및 다이어그램
- API 호출 예시 및 테스트 결과

### API 엔드포인트 목록

| 카테고리 | 메서드 | 엔드포인트 | 기능 |
|---------|--------|-----------|------|
| **감성 분석** | POST | `/api/v1/sentiment/analyze` | 리뷰 감성 비율 추출 (positive_ratio, negative_ratio) |
| | POST | `/api/v1/sentiment/analyze/batch` | 배치 감성 분석 |
| **리뷰 요약/강점** | POST | `/api/v1/llm/summarize` | 리뷰 요약 (긍정/부정/전체) |
| | POST | `/api/v1/llm/extract/strengths` | 강점 추출 (다른 리뷰들과 비교) |
| **벡터 검색** | POST | `/api/v1/vector/search/similar` | 의미 기반 리뷰 검색 |
| | POST | `/api/v1/vector/search/with-images` | 이미지가 있는 리뷰 검색 |
| | POST | `/api/v1/vector/upload` | 벡터 데이터 업로드 |
| | GET | `/api/v1/vector/restaurants/{restaurant_id}/reviews` | 레스토랑 ID로 리뷰 조회 |
| **리뷰 관리** | POST | `/api/v1/vector/reviews/upsert` | 리뷰 Upsert (낙관적 잠금 지원) |
| | POST | `/api/v1/vector/reviews/upsert/batch` | 리뷰 배치 Upsert |
| | DELETE | `/api/v1/vector/reviews/delete` | 리뷰 삭제 |
| | DELETE | `/api/v1/vector/reviews/delete/batch` | 리뷰 배치 삭제 |
| **레스토랑 조회** | GET | `/api/v1/restaurants/{restaurant_name}/reviews` | 레스토랑 이름으로 리뷰 조회 |
| **헬스 체크** | GET | `/health` | 서버 상태 확인 |
| | GET | `/` | API 기본 정보 |

### API 엔드포인트 상세

#### 1. 감성 분석 (감성 비율 추출)
```bash
POST /api/v1/sentiment/analyze
Content-Type: application/json

{
  "reviews": ["리뷰1", "리뷰2", ...],
  "restaurant_name": "레스토랑명",
  "restaurant_id": "레스토랑ID",
  "score_threshold": 0.8
}
```

**응답**: `positive_ratio`, `negative_ratio` (정수값), `positive_count`, `negative_count`, `total_count`, `llm_reclassified_count`

#### 2. 리뷰 요약 (벡터 검색 활용, 긍정/부정/전체 요약)
```bash
POST /api/v1/llm/summarize
Content-Type: application/json

{
  "restaurant_id": "res_1234",
  "positive_query": "맛있다 좋다 만족",
  "negative_query": "맛없다 별로 불만",
  "limit": 10,
  "min_score": 0.0
}
```

**응답**:
- `positive_summary`: 긍정 리뷰 요약
- `negative_summary`: 부정 리뷰 요약
- `overall_summary`: 전체 요약 (긍정 + 부정 통합)
- `positive_reviews`: 긍정 리뷰 메타데이터 리스트
- `negative_reviews`: 부정 리뷰 메타데이터 리스트
- `positive_count`, `negative_count`: 각 카테고리별 리뷰 개수

#### 3. 강점 추출 (벡터 검색 활용, 다른 리뷰들과 비교)
```bash
POST /api/v1/llm/extract/strengths
Content-Type: application/json

{
  "target_restaurant_id": "res_1234",
  "comparison_restaurant_ids": ["res_1235", "res_1236"],  # None이면 타겟 제외한 모든 레스토랑과 자동 비교
  "query": "맛있다 좋다 만족",
  "limit": 5,
  "min_score": 0.0
}
```

**응답**:
- `strength_summary`: 강점 요약
- `target_reviews`: 타겟 레스토랑 긍정 리뷰 메타데이터 리스트
- `comparison_reviews`: 비교 대상 레스토랑 긍정 리뷰 메타데이터 리스트
- `target_count`, `comparison_count`: 각 카테고리별 리뷰 개수

#### 4. 리뷰 Upsert (포인트 업데이트)
```bash
POST /api/v1/vector/reviews/upsert
Content-Type: application/json

{
  "restaurant_id": "res_1234",
  "restaurant_name": "비즐",
  "review": {
    "review_id": "rev_3001",
    "review": "맛있어요!",
    "user_id": "user_123",
    "datetime": "2024-01-01T12:00:00",
    "group": "group_1",
    "images": {"url": "http://localhost:8000/image1.jpeg"},
    "version": 1
  },
  "update_version": null  # null이면 항상 업데이트/삽입, 숫자면 해당 버전일 때만 업데이트
}
```

**응답**: 
```json
{
  "action": "inserted" | "updated" | "skipped",
  "review_id": "rev_3001",
  "version": 2,
  "point_id": "abc123...",
  "reason": null,  // skipped인 경우 "version_mismatch" 등
  "requested_version": null,
  "current_version": null
}
```

**특징**:
- **중복 방지**: 같은 review_id가 있으면 자동으로 업데이트, 없으면 삽입
- **낙관적 잠금**: `update_version`을 지정하면 해당 버전일 때만 업데이트 (동시성 제어)
- **Version 관리**: 리뷰마다 version 필드로 변경 이력 추적

#### 4-1. 리뷰 배치 Upsert (성능 최적화)
```bash
POST /api/v1/vector/reviews/upsert/batch
Content-Type: application/json

{
  "restaurant_id": "res_1234",
  "restaurant_name": "비즐",
  "reviews": [
    {
      "review_id": "rev_3001",
      "review": "맛있어요!",
      "user_id": "user_123",
      "datetime": "2024-01-01T12:00:00",
      "group": "group_1",
      "version": 1
    },
    {
      "review_id": "rev_3002",
      "review": "좋아요!",
      "user_id": "user_124",
      "datetime": "2024-01-01T12:01:00",
      "group": "group_1",
      "version": 1
    }
  ],
  "batch_size": 32
}
```

**응답**: 
```json
{
  "results": [
    {
      "action": "inserted",
      "review_id": "rev_3001",
      "version": 2,
      "point_id": "abc123..."
    },
    {
      "action": "updated",
      "review_id": "rev_3002",
      "version": 2,
      "point_id": "def456..."
    }
  ],
  "total": 2,
  "success_count": 2,
  "error_count": 0
}
```

**특징**:
- **배치 처리**: 여러 리뷰를 한 번에 처리하여 성능 향상
- **10개 리뷰를 1번의 API 호출로 처리 가능**
- **배치 벡터 인코딩**: 여러 리뷰를 한 번에 인코딩
- **배치 Qdrant upsert**: 한 번의 호출로 여러 포인트 처리
- **제한사항**: `update_filter`는 지원하지 않음 (중복 방지만 가능)

#### 4-2. 리뷰 삭제
```bash
DELETE /api/v1/vector/reviews/delete
Content-Type: application/json

{
  "restaurant_id": "res_1234",
  "review_id": "rev_3001"
}
```

**응답**: 
```json
{
  "action": "deleted" | "not_found",
  "review_id": "rev_3001",
  "point_id": "abc123..."
}
```

#### 4-3. 리뷰 배치 삭제
```bash
DELETE /api/v1/vector/reviews/delete/batch
Content-Type: application/json

{
  "restaurant_id": "res_1234",
  "review_ids": ["rev_3001", "rev_3002", "rev_3003"]
}
```

**응답**: 
```json
{
  "results": [
    {
      "action": "deleted",
      "review_id": "rev_3001",
      "point_id": "abc123..."
    }
  ],
  "total": 3,
  "deleted_count": 2,
  "not_found_count": 1
}
```

**특징**:
- **배치 처리**: 여러 리뷰를 한 번에 삭제하여 성능 향상
- **10개 리뷰를 1번의 API 호출로 처리 가능**
- 존재하지 않는 리뷰는 자동으로 건너뜀

#### 5. 이미지 리뷰 검색 (벡터 검색)
```bash
POST /api/v1/vector/search/with-images
Content-Type: application/json

{
  "query_text": "맛있다",
  "limit": 10,
  "min_score": 0.0
}
```

**응답**: 이미지 URL이 포함된 리뷰 리스트 + 모든 메타데이터

#### 6. 벡터 데이터 업로드
```bash
POST /api/v1/vector/upload
Content-Type: application/json

{
  "data": {
    "restaurants": [...]
  }
}
```

#### 7. 의미 기반 리뷰 검색 (벡터 검색)
```bash
POST /api/v1/vector/search/similar
Content-Type: application/json

{
  "query_text": "맛있다",
  "restaurant_id": "res_1234",  # 선택사항, None이면 전체 검색
  "limit": 3,
  "min_score": 0.0
}
```

**응답**: 검색된 리뷰 리스트 + 모든 메타데이터 (restaurant_id, review_id, user_id, datetime, group, image_urls, score)

#### 8. 레스토랑 리뷰 조회
```bash
GET /api/v1/vector/restaurants/{restaurant_id}/reviews
```

**응답**: 해당 레스토랑의 모든 리뷰 리스트 (메타데이터 포함)

#### 9. 레스토랑 이름으로 리뷰 조회
```bash
GET /api/v1/restaurants/{restaurant_name}/reviews
```

**응답**: 해당 레스토랑의 리뷰 리스트

### 노트북 사용

1. Jupyter Notebook 또는 JupyterLab 실행
2. `review_sentiment.ipynb` 열기
3. 셀을 순서대로 실행

### 모듈 직접 사용

```python
from src import (
    SentimentAnalyzer,
    VectorSearch,
    LLMUtils,
    get_review_list,
)

from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient

# 클라이언트 초기화
encoder = SentenceTransformer("jhgan/ko-sbert-multitask")
qdrant_client = QdrantClient(":memory:")

# LLM 유틸리티 초기화 (Qwen 모델 자동 로드)
llm_utils = LLMUtils()  # Qwen/Qwen2.5-14B-Instruct 자동 로드

# 감성 분석
analyzer = SentimentAnalyzer(llm_utils=llm_utils)
result = analyzer.analyze(review_list, "레스토랑명", "레스토랑ID")

# 벡터 검색
vector_search = VectorSearch(encoder, qdrant_client)
points = vector_search.prepare_points(data)
vector_search.upload_points(points)
```

## 성능 최적화

### 대용량 리뷰 처리
- **감성 분석**: 배치 처리 (배치 크기: 32)로 대량 리뷰 처리 속도 향상
- **벡터 인코딩**: 배치 처리 (배치 크기: 32)로 벡터 변환 최적화
- **에러 처리**: 배치 실패 시 개별 처리로 폴백하여 안정성 보장

### 벡터 검색 활용
- 모든 요약 및 강점 추출 기능에서 벡터 검색을 활용하여 관련 리뷰 자동 검색
- 의미 기반 검색으로 정확도 향상
- 메타데이터 자동 포함으로 추가 조회 불필요

## 설정

`src/config.py`에서 기본 설정을 변경할 수 있습니다:

- `SENTIMENT_MODEL`: 감성 분석 모델 (기본값: "Dilwolf/Kakao_app-kr_sentiment")
- `EMBEDDING_MODEL`: 임베딩 모델 (기본값: "jhgan/ko-sbert-multitask")
- `LLM_MODEL`: LLM 모델 (기본값: "Qwen/Qwen2.5-14B-Instruct")
- `SCORE_THRESHOLD`: 확신도 기준값 (기본값: 0.8)
- `LLM_KEYWORDS`: LLM 재분류 키워드 (기본값: ["는데", "지만"])
- `MAX_RETRIES`: LLM 호출 최대 재시도 횟수 (기본값: 3)
- `COLLECTION_NAME`: Qdrant 컬렉션 이름 (기본값: "reviews_collection")

## 라이선스

이 프로젝트는 MIT 라이선스를 따릅니다.

