# API 명세서

## 목차
1. [전체 엔드포인트 목록](#전체-엔드포인트-목록)
2. [입출력 스키마 명세](#입출력-스키마-명세)
3. [시스템 아키텍처](#시스템-아키텍처)
4. [API 호출 예시 및 테스트 결과](#api-호출-예시-및-테스트-결과)

---

## 전체 엔드포인트 목록

### 감성 분석 (Sentiment Analysis)

| 메서드 | 엔드포인트 | 기능 설명 |
|--------|-----------|----------|
| POST | `/api/v1/sentiment/analyze` | 리뷰 리스트의 감성 분석을 수행하여 `positive_ratio`, `negative_ratio`를 계산합니다. 인코더 모델(Transformers)로 1차 분석 후, 확신도가 낮거나 특정 키워드가 포함된 리뷰는 LLM으로 재분류합니다. |
| POST | `/api/v1/sentiment/analyze/batch` | 여러 레스토랑의 리뷰를 배치로 감성 분석합니다. |

### 리뷰 요약 및 강점 추출 (LLM-based Analysis)

| 메서드 | 엔드포인트 | 기능 설명 |
|--------|-----------|----------|
| POST | `/api/v1/llm/summarize` | 벡터 검색을 활용하여 긍정/부정 리뷰를 자동 검색하고 LLM으로 요약합니다. 긍정 요약, 부정 요약, 전체 요약을 모두 반환합니다. |
| POST | `/api/v1/llm/extract/strengths` | 벡터 검색을 활용하여 타겟 레스토랑과 비교 대상 레스토랑의 긍정 리뷰를 자동 검색하고, LLM으로 강점을 추출합니다. `comparison_restaurant_ids`가 None이면 타겟 제외한 모든 레스토랑과 자동 비교합니다. |

### 벡터 검색 (Vector Search)

| 메서드 | 엔드포인트 | 기능 설명 |
|--------|-----------|----------|
| POST | `/api/v1/vector/search/similar` | 의미 기반 검색(벡터 검색)을 통해 유사한 리뷰를 검색합니다. 모든 메타데이터를 포함하여 반환합니다. |
| POST | `/api/v1/vector/search/with-images` | 의미 기반 검색을 통해 이미지가 있는 리뷰를 검색합니다. 이미지 URL과 모든 메타데이터를 반환합니다. |
| POST | `/api/v1/vector/upload` | 레스토랑 데이터를 벡터 데이터베이스에 업로드합니다. (최초 1회) |
| GET | `/api/v1/vector/restaurants/{restaurant_id}/reviews` | 레스토랑 ID로 해당 레스토랑의 모든 리뷰를 조회합니다. |

### 리뷰 관리 (Review Management)

| 메서드 | 엔드포인트 | 기능 설명 |
|--------|-----------|----------|
| POST | `/api/v1/vector/reviews/upsert` | 리뷰를 upsert합니다 (있으면 업데이트, 없으면 삽입). `update_filter`를 사용하여 낙관적 잠금(Optimistic Locking)을 지원합니다. |
| POST | `/api/v1/vector/reviews/upsert/batch` | 여러 리뷰를 배치로 upsert합니다. 배치 벡터 인코딩과 배치 Qdrant upsert를 통해 성능을 최적화합니다. |
| DELETE | `/api/v1/vector/reviews/delete` | 리뷰를 삭제합니다. `review_id`를 기반으로 Point ID를 생성하여 삭제합니다. |
| DELETE | `/api/v1/vector/reviews/delete/batch` | 여러 리뷰를 배치로 삭제합니다. |

### 레스토랑 조회 (Restaurant Lookup)

| 메서드 | 엔드포인트 | 기능 설명 |
|--------|-----------|----------|
| GET | `/api/v1/restaurants/{restaurant_name}/reviews` | 레스토랑 이름으로 해당 레스토랑의 리뷰를 조회합니다. |

### 헬스 체크 (Health Check)

| 메서드 | 엔드포인트 | 기능 설명 |
|--------|-----------|----------|
| GET | `/health` | 서버 상태를 확인합니다. |
| GET | `/` | API 기본 정보를 반환합니다. |

---

## 입출력 스키마 명세

### 1. 감성 분석

#### 요청: `POST /api/v1/sentiment/analyze`

```json
{
  "reviews": ["리뷰1", "리뷰2", ...],
  "restaurant_name": "레스토랑명",
  "restaurant_id": "레스토랑ID",
  "score_threshold": 0.8,
  "llm_keywords": ["는데", "지만"]
}
```

**필드 설명:**
- `reviews` (required, List[str]): 분석할 리뷰 텍스트 리스트
- `restaurant_name` (required, str): 레스토랑 이름
- `restaurant_id` (required, str): 레스토랑 ID
- `score_threshold` (optional, float, default: 0.8): 확신도 기준값 (이 값 미만이면 LLM 재분류)
- `llm_keywords` (optional, List[str]): LLM 재분류 키워드

#### 응답: `SentimentResponse`

```json
{
  "restaurant_name": "비즐",
  "restaurant_id": "res_1234",
  "positive_count": 3,
  "negative_count": 2,
  "total_count": 5,
  "positive_ratio": 60,
  "negative_ratio": 40,
  "llm_reclassified_count": 3
}
```

**필드 설명:**
- `restaurant_name` (str): 레스토랑 이름
- `restaurant_id` (str): 레스토랑 ID
- `positive_count` (int): 긍정 리뷰 개수
- `negative_count` (int): 부정 리뷰 개수
- `total_count` (int): 전체 리뷰 개수
- `positive_ratio` (int): 긍정 비율 (%)
- `negative_ratio` (int): 부정 비율 (%)
- `llm_reclassified_count` (int): LLM으로 재분류된 리뷰 개수

---

### 2. 리뷰 요약

#### 요청: `POST /api/v1/llm/summarize`

```json
{
  "restaurant_id": "res_1234",
  "positive_query": "맛있다 좋다 만족",
  "negative_query": "맛없다 별로 불만",
  "limit": 10,
  "min_score": 0.0
}
```

**필드 설명:**
- `restaurant_id` (required, str): 레스토랑 ID
- `positive_query` (optional, str, default: "맛있다 좋다 만족"): 긍정 리뷰 검색 쿼리
- `negative_query` (optional, str, default: "맛없다 별로 불만"): 부정 리뷰 검색 쿼리
- `limit` (optional, int, default: 10, range: 1-100): 각 카테고리당 검색할 최대 리뷰 수
- `min_score` (optional, float, default: 0.0, range: 0.0-1.0): 최소 유사도 점수

#### 응답: `SummarizeResponse`

```json
{
  "restaurant_id": "res_1234",
  "positive_summary": "가츠동이 괜찮고, 웨이팅이 길지 않고 회전이 빨라 편리하다.",
  "negative_summary": "음식이 짜고 다른 메뉴는 애매하며 점심시간에 붐빈다.",
  "overall_summary": "가츠동과 빠른 회전이 장점인 반면, 음식이 다소 짜고 일부 메뉴는 만족스럽지 않다.",
  "positive_reviews": [
    {
      "restaurant_id": "res_1234",
      "restaurant_name": "비즐",
      "review_id": "rev_3001",
      "user_id": "user_2001",
      "datetime": "2026-01-03 12:10:00",
      "group": "카카오",
      "review": "점심시간이라 사람이 많았지만 생각보다 빨리 나왔다.",
      "image_urls": []
    }
  ],
  "negative_reviews": [
    {
      "restaurant_id": "res_1234",
      "restaurant_name": "비즐",
      "review_id": "rev_3002",
      "user_id": "user_2002",
      "datetime": "2026-01-03 12:12:00",
      "group": "네이버",
      "review": "가츠동은 괜찮았는데 다른 메뉴는 좀 애매했다.",
      "image_urls": []
    }
  ],
  "positive_count": 3,
  "negative_count": 2
}
```

**필드 설명:**
- `restaurant_id` (str): 레스토랑 ID
- `positive_summary` (str): 긍정 리뷰 요약
- `negative_summary` (str): 부정 리뷰 요약
- `overall_summary` (str): 전체 요약 (긍정 + 부정 통합)
- `positive_reviews` (List[Dict]): 긍정 리뷰 메타데이터 리스트
- `negative_reviews` (List[Dict]): 부정 리뷰 메타데이터 리스트
- `positive_count` (int): 긍정 리뷰 개수
- `negative_count` (int): 부정 리뷰 개수

---

### 3. 강점 추출

#### 요청: `POST /api/v1/llm/extract/strengths`

```json
{
  "target_restaurant_id": "res_1234",
  "comparison_restaurant_ids": ["res_1235", "res_1236"],
  "query": "맛있다 좋다 만족",
  "limit": 5,
  "min_score": 0.0
}
```

**필드 설명:**
- `target_restaurant_id` (required, str): 타겟 레스토랑 ID
- `comparison_restaurant_ids` (optional, List[str] or null): 비교 대상 레스토랑 ID 리스트 (None이면 타겟 제외한 모든 레스토랑과 자동 비교)
- `query` (optional, str, default: "맛있다 좋다 만족"): 긍정 리뷰 검색 쿼리
- `limit` (optional, int, default: 5, range: 1-50): 각 레스토랑당 검색할 최대 리뷰 수
- `min_score` (optional, float, default: 0.0, range: 0.0-1.0): 최소 유사도 점수

#### 응답: `ExtractStrengthsResponse`

```json
{
  "target_restaurant_id": "res_1234",
  "strength_summary": "이 음식점은 음식 맛이 대체로 무난하며 실패 확률이 적고, 가츠동 메뉴가 상대적으로 괜찮다는 평가를 받는다.",
  "target_reviews": [
    {
      "restaurant_id": "res_1234",
      "restaurant_name": "비즐",
      "review_id": "rev_3001",
      "user_id": "user_2001",
      "datetime": "2026-01-03 12:10:00",
      "group": "카카오",
      "review": "점심시간이라 사람이 많았지만 생각보다 빨리 나왔다.",
      "image_urls": []
    }
  ],
  "comparison_reviews": [
    {
      "restaurant_id": "res_1235",
      "restaurant_name": "시올돈",
      "review_id": "rev_4001",
      "user_id": "user_2101",
      "datetime": "2026-02-03 18:00:00",
      "group": "카카오",
      "review": "음식 맛은 무난하고 실패는 없는 편이다.",
      "image_urls": []
    }
  ],
  "target_count": 3,
  "comparison_count": 5
}
```

**필드 설명:**
- `target_restaurant_id` (str): 타겟 레스토랑 ID
- `strength_summary` (str): 강점 요약
- `target_reviews` (List[Dict]): 타겟 레스토랑 긍정 리뷰 메타데이터 리스트
- `comparison_reviews` (List[Dict]): 비교 대상 레스토랑 긍정 리뷰 메타데이터 리스트
- `target_count` (int): 타겟 리뷰 개수
- `comparison_count` (int): 비교 리뷰 개수

---

### 4. 리뷰 Upsert

#### 요청: `POST /api/v1/vector/reviews/upsert`

```json
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
  "update_version": null
}
```

**필드 설명:**
- `restaurant_id` (required, str): 레스토랑 ID
- `restaurant_name` (required, str): 레스토랑 이름
- `review` (required, Dict): 리뷰 딕셔너리
  - `review_id` (required, str): 리뷰 ID
  - `review` (required, str): 리뷰 텍스트
  - `user_id` (required, str): 사용자 ID
  - `datetime` (required, str): 날짜/시간
  - `group` (required, str): 그룹 (예: "카카오", "네이버")
  - `images` (optional, Dict): 이미지 정보
  - `version` (required, int): 버전 번호
- `update_version` (optional, int or null): 업데이트할 버전 (None이면 항상 업데이트/삽입, 지정하면 해당 버전일 때만 업데이트)

#### 응답: `UpsertReviewResponse`

```json
{
  "action": "inserted",
  "review_id": "rev_3001",
  "version": 2,
  "point_id": "abc123def456...",
  "reason": null,
  "requested_version": null,
  "current_version": null
}
```

**필드 설명:**
- `action` (str): 수행된 작업 ("inserted", "updated", "skipped")
- `review_id` (str): 리뷰 ID
- `version` (int): 새로운 버전 번호
- `point_id` (str): Point ID (MD5 해시)
- `reason` (str or null): skipped인 경우 이유 ("version_mismatch" 등)
- `requested_version` (int or null): 요청한 버전 (skipped인 경우)
- `current_version` (int or null): 현재 버전 (skipped인 경우)

---

### 5. 리뷰 배치 Upsert

#### 요청: `POST /api/v1/vector/reviews/upsert/batch`

```json
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
    }
  ],
  "batch_size": 32
}
```

**필드 설명:**
- `restaurant_id` (required, str): 레스토랑 ID
- `restaurant_name` (required, str): 레스토랑 이름
- `reviews` (required, List[Dict]): 리뷰 딕셔너리 리스트
- `batch_size` (optional, int, default: 32, range: 1-100): 벡터 인코딩 배치 크기

#### 응답: `UpsertReviewsBatchResponse`

```json
{
  "results": [
    {
      "action": "inserted",
      "review_id": "rev_3001",
      "version": 2,
      "point_id": "abc123..."
    }
  ],
  "total": 1,
  "success_count": 1,
  "error_count": 0
}
```

---

### 6. 리뷰 삭제

#### 요청: `DELETE /api/v1/vector/reviews/delete`

```json
{
  "restaurant_id": "res_1234",
  "review_id": "rev_3001"
}
```

#### 응답: `DeleteReviewResponse`

```json
{
  "action": "deleted",
  "review_id": "rev_3001",
  "point_id": "abc123def456..."
}
```

---

### 7. 의미 기반 리뷰 검색

#### 요청: `POST /api/v1/vector/search/similar`

```json
{
  "query_text": "맛있다",
  "restaurant_id": "res_1234",
  "limit": 3,
  "min_score": 0.0
}
```

**필드 설명:**
- `query_text` (required, str): 검색 쿼리 텍스트
- `restaurant_id` (optional, str or null): 레스토랑 ID 필터 (None이면 전체 검색)
- `limit` (optional, int, default: 3, range: 1-100): 반환할 최대 개수
- `min_score` (optional, float, default: 0.0, range: 0.0-1.0): 최소 유사도 점수

#### 응답: `SimilarReviewResponse`

```json
{
  "results": [
    {
      "payload": {
        "restaurant_id": "res_1234",
        "restaurant_name": "비즐",
        "review_id": "rev_3001",
        "user_id": "user_2001",
        "datetime": "2026-01-03 12:10:00",
        "group": "카카오",
        "review": "맛있어요!",
        "image_urls": []
      },
      "score": 0.85
    }
  ],
  "total": 1
}
```

---

## 시스템 아키텍처

### 전체 시스템 구조

```
┌─────────────────────────────────────────────────────────────────┐
│                         Client (API Consumer)                    │
└────────────────────────────┬────────────────────────────────────┘
                             │ HTTP/REST API
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                      FastAPI Application                        │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  API Routers                                              │  │
│  │  ├── /api/v1/sentiment/*  (감성 분석)                    │  │
│  │  ├── /api/v1/llm/*        (요약/강점 추출)                │  │
│  │  ├── /api/v1/vector/*     (벡터 검색/관리)                │  │
│  │  └── /api/v1/restaurants/* (레스토랑 조회)                 │  │
│  └──────────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Core Services                                           │  │
│  │  ├── SentimentAnalyzer    (감성 분석)                    │  │
│  │  ├── VectorSearch         (벡터 검색)                    │  │
│  │  └── LLMUtils             (LLM 요약/강점 추출)            │  │
│  └──────────────────────────────────────────────────────────┘  │
└────────────────────────────┬────────────────────────────────────┘
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
        ▼                    ▼                    ▼
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│  Transformers│    │ Sentence     │    │  Qwen2.5-14B │
│  Pipeline    │    │ Transformer  │    │  Instruct    │
│  (Sentiment)  │    │ (Embedding)  │    │  (Local LLM) │
└──────────────┘    └──────┬───────┘    └──────────────┘
                            │
                            ▼
                    ┌──────────────┐
                    │   Qdrant     │
                    │  (Vector DB) │
                    │  :memory: or │
                    │  Remote URL  │
                    └──────────────┘
```

### 데이터 흐름

#### 1. 감성 분석 흐름
```
리뷰 텍스트 리스트
    │
    ▼
[Transformers Pipeline] → 1차 감성 분석 (긍정/부정)
    │
    ├─ 확신도 높음 → 최종 결과
    └─ 확신도 낮음 또는 특정 키워드 포함
        │
        ▼
    [Qwen2.5-14B-Instruct] → 2차 재분류 (로컬 LLM)
        │
        ▼
    최종 결과 (positive_ratio, negative_ratio)
```

#### 2. 리뷰 요약 흐름
```
요청 (restaurant_id, positive_query, negative_query)
    │
    ├─ [VectorSearch] → 긍정 리뷰 검색 (벡터 검색)
    └─ [VectorSearch] → 부정 리뷰 검색 (벡터 검색)
        │
        ▼
    검색된 리뷰 메타데이터
        │
        ▼
    [Qwen2.5-14B-Instruct] → 긍정/부정/전체 요약 생성 (로컬 LLM)
        │
        ▼
    응답 (요약 + 메타데이터)
```

#### 3. 강점 추출 흐름
```
요청 (target_restaurant_id, comparison_restaurant_ids, query)
    │
    ├─ [VectorSearch] → 타겟 레스토랑 긍정 리뷰 검색
    └─ [VectorSearch] → 비교 대상 레스토랑 긍정 리뷰 검색
        │
        ▼
    검색된 리뷰 메타데이터
        │
        ▼
    [Qwen2.5-14B-Instruct] → 강점 추출 (로컬 LLM)
        │
        ▼
    응답 (강점 요약 + 메타데이터)
```

#### 4. 리뷰 Upsert 흐름
```
요청 (restaurant_id, review, update_version)
    │
    ├─ Point ID 생성 (MD5 해시: restaurant_id + review_id)
    ├─ [SentenceTransformer] → 리뷰 텍스트 벡터 인코딩
    └─ [Qdrant] → Upsert (update_filter로 낙관적 잠금)
        │
        ▼
    응답 (action, version, point_id)
```

### 컴포넌트 역할

| 컴포넌트 | 역할 | 기술 스택 |
|---------|------|----------|
| **FastAPI Application** | REST API 서버, 라우팅, 의존성 주입 | FastAPI, Uvicorn |
| **SentimentAnalyzer** | 감성 분석 (인코더 + LLM 하이브리드) | Transformers, Qwen |
| **VectorSearch** | 벡터 검색, 리뷰 관리 (CRUD) | SentenceTransformer, Qdrant |
| **LLMUtils** | LLM 기반 요약 및 강점 추출 | Qwen2.5-14B-Instruct (로컬) |
| **Qdrant** | 벡터 데이터베이스 | Qdrant (in-memory or remote) |
| **SentenceTransformer** | 텍스트 임베딩 생성 | jhgan/ko-sbert-multitask |
| **Transformers Pipeline** | 1차 감성 분석 | Dilwolf/Kakao_app-kr_sentiment |
| **Qwen2.5-14B-Instruct** | 로컬 LLM 모델 | Hugging Face Transformers, PyTorch |

### 서비스 연동 관계

```
┌─────────────────────────────────────────────────────────────┐
│                    Review Analysis API                       │
│                                                              │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐  │
│  │  Sentiment   │───▶│   Vector    │───▶│     LLM      │  │
│  │  Analysis    │    │   Search    │    │   Utils      │  │
│  └──────┬───────┘    └──────┬──────┘    └──────┬──────┘  │
│         │                    │                   │          │
│         │                    │                   │          │
│    ┌────▼────┐          ┌────▼────┐        ┌────▼────┐   │
│    │Transform│          │Sentence │        │  Qwen   │   │
│    │Pipeline │          │Transform│        │2.5-14B  │   │
│    └─────────┘          └────┬────┘        │Instruct │   │
│                              │             └─────────┘   │
│                              │                          │
│                         ┌────▼────┐                    │
│                         │  Qdrant  │                    │
│                         │ VectorDB │                    │
│                         └──────────┘                    │
└──────────────────────────────────────────────────────────┘
```

---

## API 호출 예시 및 테스트 결과

### 테스트 환경
- **서버**: FastAPI (Uvicorn)
- **포트**: 8000
- **Qdrant**: In-memory mode (`:memory:`)
- **LLM 모델**: Qwen/Qwen2.5-14B-Instruct (로컬)
- **테스트 파일**: `test_api.ipynb`

### 1. 감성 분석 테스트

**요청:**
```bash
curl -X POST "http://localhost:8000/api/v1/sentiment/analyze" \
  -H "Content-Type: application/json" \
  -d '{
    "reviews": [
      "점심시간이라 사람이 많았지만 생각보다 빨리 나왔다.",
      "가츠동은 괜찮았는데 다른 메뉴는 좀 애매했다."
    ],
    "restaurant_name": "비즐",
    "restaurant_id": "res_1234"
  }'
```

**응답:**
```json
{
  "restaurant_name": "비즐",
  "restaurant_id": "res_1234",
  "positive_count": 1,
  "negative_count": 1,
  "total_count": 2,
  "positive_ratio": 50,
  "negative_ratio": 50,
  "llm_reclassified_count": 2
}
```

**테스트 결과**: ✅ 성공
- LLM 재분류가 정상 작동
- 비율이 정수값으로 반환됨

---

### 2. 리뷰 요약 테스트

**요청:**
```bash
curl -X POST "http://localhost:8000/api/v1/llm/summarize" \
  -H "Content-Type: application/json" \
  -d '{
    "restaurant_id": "res_1234",
    "positive_query": "맛있다 좋다 만족",
    "negative_query": "맛없다 별로 불만",
    "limit": 10
  }'
```

**응답:**
```json
{
  "restaurant_id": "res_1234",
  "positive_summary": "가츠동이 괜찮고, 웨이팅이 길지 않고 회전이 빨라 편리하다.",
  "negative_summary": "음식이 짜고 다른 메뉴는 애매하며 점심시간에 붐빈다.",
  "overall_summary": "가츠동과 빠른 회전이 장점인 반면, 음식이 다소 짜고 일부 메뉴는 만족스럽지 않다.",
  "positive_reviews": [...],
  "negative_reviews": [...],
  "positive_count": 3,
  "negative_count": 2
}
```

**테스트 결과**: ✅ 성공
- 벡터 검색으로 긍정/부정 리뷰 자동 검색
- 긍정/부정/전체 요약 모두 생성
- 메타데이터 포함

---

### 3. 강점 추출 테스트

**요청:**
```bash
curl -X POST "http://localhost:8000/api/v1/llm/extract/strengths" \
  -H "Content-Type: application/json" \
  -d '{
    "target_restaurant_id": "res_1234",
    "comparison_restaurant_ids": null,
    "query": "맛있다 좋다 만족",
    "limit": 5
  }'
```

**응답:**
```json
{
  "target_restaurant_id": "res_1234",
  "strength_summary": "이 음식점은 음식 맛이 대체로 무난하며 실패 확률이 적고, 가츠동 메뉴가 상대적으로 괜찮다는 평가를 받는다.",
  "target_reviews": [...],
  "comparison_reviews": [...],
  "target_count": 3,
  "comparison_count": 5
}
```

**테스트 결과**: ✅ 성공
- `comparison_restaurant_ids`가 `null`일 때 타겟 제외한 모든 레스토랑과 자동 비교
- 벡터 검색으로 관련 리뷰 자동 검색
- 메타데이터 포함

---

### 4. 리뷰 Upsert 테스트

**요청:**
```bash
curl -X POST "http://localhost:8000/api/v1/vector/reviews/upsert" \
  -H "Content-Type: application/json" \
  -d '{
    "restaurant_id": "res_1234",
    "restaurant_name": "비즐",
    "review": {
      "review_id": "rev_3001",
      "review": "맛있어요!",
      "user_id": "user_123",
      "datetime": "2024-01-01T12:00:00",
      "group": "group_1",
      "version": 1
    },
    "update_version": null
  }'
```

**응답:**
```json
{
  "action": "inserted",
  "review_id": "rev_3001",
  "version": 2,
  "point_id": "abc123def456...",
  "reason": null,
  "requested_version": null,
  "current_version": null
}
```

**테스트 결과**: ✅ 성공
- 리뷰가 정상적으로 삽입됨
- Point ID가 MD5 해시로 생성됨
- Version이 자동 증가

---

### 5. 배치 Upsert 테스트

**요청:**
```bash
curl -X POST "http://localhost:8000/api/v1/vector/reviews/upsert/batch" \
  -H "Content-Type: application/json" \
  -d '{
    "restaurant_id": "res_1234",
    "restaurant_name": "비즐",
    "reviews": [
      {"review_id": "rev_3001", "review": "맛있어요!", ...},
      {"review_id": "rev_3002", "review": "좋아요!", ...}
    ],
    "batch_size": 32
  }'
```

**응답:**
```json
{
  "results": [
    {"action": "inserted", "review_id": "rev_3001", ...},
    {"action": "inserted", "review_id": "rev_3002", ...}
  ],
  "total": 2,
  "success_count": 2,
  "error_count": 0
}
```

**테스트 결과**: ✅ 성공
- 10개 리뷰를 1번의 API 호출로 처리
- 배치 벡터 인코딩으로 성능 최적화

---

### 6. 리뷰 삭제 테스트

**요청:**
```bash
curl -X DELETE "http://localhost:8000/api/v1/vector/reviews/delete" \
  -H "Content-Type: application/json" \
  -d '{
    "restaurant_id": "res_1234",
    "review_id": "rev_3001"
  }'
```

**응답:**
```json
{
  "action": "deleted",
  "review_id": "rev_3001",
  "point_id": "abc123def456..."
}
```

**테스트 결과**: ✅ 성공
- 리뷰가 정상적으로 삭제됨

---

## 참고 문서

- **상세 사용 가이드**: [API_USAGE.md](API_USAGE.md)
- **프로젝트 개요**: [README.md](README.md)
- **프로젝트 점검**: [PROJECT_REVIEW.md](PROJECT_REVIEW.md)
- **추론 최적화**: [INFERENCE_OPTIMIZATION.md](INFERENCE_OPTIMIZATION.md)
- **API 테스트 노트북**: `test_api.ipynb`

---

## API 문서 (Swagger/ReDoc)

실행 중인 서버에서 다음 URL로 상세한 API 문서를 확인할 수 있습니다:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

이 문서들은 Pydantic 모델을 기반으로 자동 생성되며, 모든 엔드포인트의 요청/응답 스키마를 확인할 수 있습니다.

