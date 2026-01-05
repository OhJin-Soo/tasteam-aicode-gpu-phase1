# API 사용 가이드

> **📋 전체 API 명세서**: [API_SPECIFICATION.md](API_SPECIFICATION.md)에서 다음을 확인할 수 있습니다:
> - 전체 엔드포인트 목록 및 기능 설명
> - 입출력 스키마 명세 (JSON Schema)
> - 시스템 아키텍처 및 다이어그램
> - API 호출 예시 및 테스트 결과

## ✅ 지원하는 기능

현재 API는 다음 기능들을 지원합니다:

1. **리뷰 감성 비율 추출** (positive_ratio, negative_ratio)
2. **리뷰 요약** (긍정/부정/전체 요약)
3. **다른 리뷰들과의 강점 추출**
4. **리뷰 Upsert** (포인트 업데이트, 낙관적 잠금 지원)
5. **이미지 리뷰 검색** (이미지 추출 목적)
6. **벡터 데이터 업로드** (최초 데이터 업로드)
7. **의미 기반 리뷰 검색** (벡터 검색)
8. **레스토랑 리뷰 조회** (레스토랑 ID/이름으로 조회)

---

## 1. 리뷰 감성 비율 추출

### 엔드포인트
```
POST /api/v1/sentiment/analyze
```

### 요청 예시
```bash
curl -X POST "http://localhost:8000/api/v1/sentiment/analyze" \
  -H "Content-Type: application/json" \
  -d '{
    "reviews": [
      "점심시간이라 사람이 많았지만 생각보다 빨리 나왔다.",
      "가츠동은 괜찮았는데 다른 메뉴는 좀 애매했다.",
      "직원 응대가 그날그날 다른 느낌이다.",
      "음식은 맛있을 때도 있지만 오늘은 좀 짰다.",
      "웨이팅이 길 줄 알았는데 회전이 빨라서 괜찮았다."
    ],
    "restaurant_name": "비즐",
    "restaurant_id": "res_1234",
    "score_threshold": 0.8
  }'
```

### 응답 예시
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

### Python 예시
```python
import requests

url = "http://localhost:8000/api/v1/sentiment/analyze"
data = {
    "reviews": [
        "점심시간이라 사람이 많았지만 생각보다 빨리 나왔다.",
        "가츠동은 괜찮았는데 다른 메뉴는 좀 애매했다.",
    ],
    "restaurant_name": "비즐",
    "restaurant_id": "res_1234"
}

response = requests.post(url, json=data)
result = response.json()

print(f"긍정 비율: {result['positive_ratio']}%")
print(f"부정 비율: {result['negative_ratio']}%")
```

---

## 2. 리뷰 요약 (벡터 검색 활용)

### 엔드포인트
```
POST /api/v1/llm/summarize
```

### 요청 예시
```bash
curl -X POST "http://localhost:8000/api/v1/llm/summarize" \
  -H "Content-Type: application/json" \
  -d '{
    "restaurant_id": "res_1234",
    "positive_query": "맛있다 좋다 만족",
    "negative_query": "맛없다 별로 불만",
    "limit": 10,
    "min_score": 0.0
  }'
```

**특징**: 벡터 검색을 통해 긍정/부정 리뷰를 자동으로 검색하고 요약합니다.

### 응답 예시
```json
{
  "restaurant_id": "res_1234",
  "positive_summary": "가츠동이 괜찮고, 웨이팅이 길지 않고 회전이 빨라 편리하다. 직원들이 전반적으로 친절하다.",
  "negative_summary": "음식이 짜고 다른 메뉴는 애매하며 점심시간에 붐빈다. 직원 응대가 일관성이 없다.",
  "overall_summary": "가츠동과 빠른 회전이 장점인 반면, 음식이 다소 짜고 일부 메뉴는 만족스럽지 않으며 점심시간에 붐빈다.",
  "positive_reviews": [
    {
      "restaurant_id": "res_1234",
      "restaurant_name": "비즐",
      "review_id": "rev_3001",
      "user_id": "user_2001",
      "datetime": "2026-01-03 12:10:00",
      "group": "카카오",
      "review": "점심시간이라 사람이 많았지만 생각보다 빨리 나왔다.",
      "image_urls": ["http://localhost:8000/bizzle_image1.jpeg"]
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

### Python 예시
```python
import requests

url = "http://localhost:8000/api/v1/llm/summarize"
data = {
    "restaurant_id": "res_1234",
    "positive_query": "맛있다 좋다 만족",
    "negative_query": "맛없다 별로 불만",
    "limit": 10
}

response = requests.post(url, json=data)
result = response.json()

# 긍정/부정/전체 요약 모두 출력
print(f"✅ 긍정 요약: {result['positive_summary']}")
print(f"✅ 부정 요약: {result['negative_summary']}")
print(f"✅ 전체 요약: {result['overall_summary']}")
print(f"✅ 긍정 리뷰 {result['positive_count']}개, 부정 리뷰 {result['negative_count']}개")
```

---

## 3. 다른 리뷰들과의 강점 추출 (벡터 검색 활용)

### 엔드포인트
```
POST /api/v1/llm/extract/strengths
```

### 요청 예시
```bash
curl -X POST "http://localhost:8000/api/v1/llm/extract/strengths" \
  -H "Content-Type: application/json" \
  -d '{
    "target_restaurant_id": "res_1234",
    "comparison_restaurant_ids": ["res_1235", "res_1236"],
    "query": "맛있다 좋다 만족",
    "limit": 5,
    "min_score": 0.0
  }'
```

**특징**: 벡터 검색을 통해 타겟 및 비교 대상 레스토랑의 긍정 리뷰를 자동으로 검색하고 강점을 추출합니다.

**비교 대상이 None인 경우**: 타겟 레스토랑을 제외한 모든 레스토랑과 자동으로 비교합니다.
- 시스템이 컬렉션에서 모든 레스토랑 ID를 자동으로 조회
- 타겟 레스토랑을 제외한 모든 레스토랑에 대해 각각 검색 수행
- 모든 레스토랑의 리뷰를 포함하여 정확한 비교 수행

### 응답 예시
```json
{
  "target_restaurant_id": "res_1234",
  "strength_summary": "이 음식점은 음식 맛이 대체로 무난하며 실패 확률이 적고, 가츠동 메뉴가 상대적으로 괜찮다는 평가를 받는다. 또한 긴 웨이팅을 예상했지만 회전이 빨라 대기 시간이 적은 점과 직원들의 친절함이 긍정적으로 평가된다.",
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
      "image_urls": ["http://localhost:8000/sioldon_image1.jpeg"]
    }
  ],
  "target_count": 3,
  "comparison_count": 5
}
```

### Python 예시
```python
import requests

url = "http://localhost:8000/api/v1/llm/extract/strengths"
data = {
    "target_restaurant_id": "res_1234",
    "comparison_restaurant_ids": ["res_1235", "res_1236"],  # None이면 타겟 제외한 모든 레스토랑과 자동 비교
    "query": "맛있다 좋다 만족",
    "limit": 5,
    "min_score": 0.0
}

response = requests.post(url, json=data)
result = response.json()

print(f"✅ 강점: {result['strength_summary']}")
print(f"✅ 타겟 리뷰 {result['target_count']}개, 비교 리뷰 {result['comparison_count']}개")
print(f"✅ 메타데이터 포함: {len(result['target_reviews'])}개 타겟 리뷰")
```

---

## 4. 리뷰 Upsert (포인트 업데이트)

### 엔드포인트
```
POST /api/v1/vector/reviews/upsert
```

### 설명
리뷰를 upsert합니다 (있으면 업데이트, 없으면 삽입).
`update_filter`를 사용하여 낙관적 잠금(Optimistic Locking)을 지원합니다.

**동작 방식:**
1. `update_version`이 None이면: 항상 업데이트/삽입 (중복 방지)
2. `update_version`이 지정되면: 해당 버전일 때만 업데이트 (낙관적 잠금)

**사용 시나리오:**
- **리뷰 추가/수정 (중복 방지)**: `update_version=None`
  - 같은 review_id가 있으면 자동으로 업데이트
  - 없으면 새로 삽입
  
- **리뷰 수정 (동시성 제어)**: `update_version=3`
  - 현재 버전이 3일 때만 업데이트
  - 다른 사용자가 먼저 수정했다면 (version이 4 이상) 스킵

### 요청 예시 (중복 방지)
```bash
curl -X POST "http://localhost:8000/api/v1/vector/reviews/upsert" \
  -H "Content-Type: application/json" \
  -d '{
    "restaurant_id": "res_1234",
    "restaurant_name": "비즐",
    "review": {
      "review_id": "rev_3001",
      "review": "맛있어요! 수정된 리뷰입니다.",
      "user_id": "user_123",
      "datetime": "2024-01-01T12:00:00",
      "group": "group_1",
      "images": {"url": "http://localhost:8000/image1.jpeg"},
      "version": 1
    },
    "update_version": null
  }'
```

### 요청 예시 (낙관적 잠금)
```bash
curl -X POST "http://localhost:8000/api/v1/vector/reviews/upsert" \
  -H "Content-Type: application/json" \
  -d '{
    "restaurant_id": "res_1234",
    "restaurant_name": "비즐",
    "review": {
      "review_id": "rev_3001",
      "review": "맛있어요! 수정된 리뷰입니다.",
      "user_id": "user_123",
      "datetime": "2024-01-01T12:00:00",
      "group": "group_1",
      "version": 3
    },
    "update_version": 3
  }'
```

### 응답 예시 (성공)
```json
{
  "action": "updated",
  "review_id": "rev_3001",
  "version": 4,
  "point_id": "abc123def456...",
  "reason": null,
  "requested_version": 3,
  "current_version": null
}
```

### 응답 예시 (버전 불일치 - 스킵)
```json
{
  "action": "skipped",
  "review_id": "rev_3001",
  "version": 4,
  "point_id": "abc123def456...",
  "reason": "version_mismatch",
  "requested_version": 3,
  "current_version": 4
}
```

### Python 예시
```python
import requests

url = "http://localhost:8000/api/v1/vector/reviews/upsert"

# 시나리오 1: 리뷰 추가/수정 (중복 방지)
data = {
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
    "update_version": None  # 항상 업데이트/삽입
}

response = requests.post(url, json=data)
result = response.json()

print(f"✅ 작업: {result['action']}")  # "inserted" 또는 "updated"
print(f"✅ 버전: {result['version']}")

# 시나리오 2: 리뷰 수정 (동시성 제어)
data = {
    "restaurant_id": "res_1234",
    "restaurant_name": "비즐",
    "review": {
        "review_id": "rev_3001",
        "review": "수정된 리뷰 내용",
        "user_id": "user_123",
        "datetime": "2024-01-01T12:00:00",
        "group": "group_1",
        "version": 3
    },
    "update_version": 3  # 버전 3일 때만 업데이트
}

response = requests.post(url, json=data)
result = response.json()

if result["action"] == "skipped":
    print(f"⚠️ 스킵됨: {result['reason']}")
    print(f"   요청 버전: {result['requested_version']}")
    print(f"   현재 버전: {result['current_version']}")
else:
    print(f"✅ 업데이트 완료: 버전 {result['version']}")
```

---

## 4-1. 리뷰 배치 Upsert (성능 최적화)

### 엔드포인트
```
POST /api/v1/vector/reviews/upsert/batch
```

### 설명
여러 리뷰를 배치로 upsert합니다. (성능 최적화)

**특징:**
- **배치 벡터 인코딩**: 여러 리뷰를 한 번에 인코딩하여 성능 향상
- **배치 Qdrant upsert**: 한 번의 API 호출로 여러 리뷰 처리
- **10개 리뷰를 1번의 API 호출로 처리 가능**

**제한사항:**
- `update_filter`는 지원하지 않습니다 (중복 방지만 가능)
- 낙관적 잠금이 필요한 경우 개별 upsert 엔드포인트 사용

### 요청 예시
```bash
curl -X POST "http://localhost:8000/api/v1/vector/reviews/upsert/batch" \
  -H "Content-Type: application/json" \
  -d '{
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
  }'
```

### 응답 예시
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

### Python 예시
```python
import requests

url = "http://localhost:8000/api/v1/vector/reviews/upsert/batch"

# 10개 리뷰를 한 번에 처리
data = {
    "restaurant_id": "res_1234",
    "restaurant_name": "비즐",
    "reviews": [
        {
            "review_id": f"rev_{i:04d}",
            "review": f"리뷰 내용 {i}",
            "user_id": f"user_{i}",
            "datetime": "2024-01-01T12:00:00",
            "group": "group_1",
            "version": 1
        }
        for i in range(1, 11)  # 10개 리뷰
    ],
    "batch_size": 32
}

response = requests.post(url, json=data)
result = response.json()

print(f"✅ 총 {result['total']}개 리뷰 처리")
print(f"✅ 성공: {result['success_count']}개")
print(f"❌ 실패: {result['error_count']}개")

# 각 리뷰 결과 확인
for r in result["results"]:
    print(f"  - {r['review_id']}: {r['action']} (version {r['version']})")
```

**성능 비교:**
- **개별 upsert**: 10개 리뷰 = 10번 API 호출 + 10번 벡터 인코딩 + 10번 Qdrant upsert
- **배치 upsert**: 10개 리뷰 = 1번 API 호출 + 1번 배치 벡터 인코딩 + 1번 배치 Qdrant upsert

---

## 4-2. 리뷰 삭제

### 엔드포인트
```
DELETE /api/v1/vector/reviews/delete
```

### 설명
리뷰를 삭제합니다. review_id를 기반으로 Point ID를 생성하여 삭제합니다.

**동작 방식:**
- review_id를 기반으로 Point ID를 생성하여 삭제
- 리뷰가 존재하지 않으면 "not_found" 반환

### 요청 예시
```bash
curl -X DELETE "http://localhost:8000/api/v1/vector/reviews/delete" \
  -H "Content-Type: application/json" \
  -d '{
    "restaurant_id": "res_1234",
    "review_id": "rev_3001"
  }'
```

### 응답 예시 (성공)
```json
{
  "action": "deleted",
  "review_id": "rev_3001",
  "point_id": "abc123def456..."
}
```

### 응답 예시 (리뷰 없음)
```json
{
  "action": "not_found",
  "review_id": "rev_3001",
  "point_id": "abc123def456..."
}
```

### Python 예시
```python
import requests

url = "http://localhost:8000/api/v1/vector/reviews/delete"
data = {
    "restaurant_id": "res_1234",
    "review_id": "rev_3001"
}

response = requests.delete(url, json=data)
result = response.json()

if result["action"] == "deleted":
    print(f"✅ 리뷰 {result['review_id']} 삭제 완료")
else:
    print(f"⚠️ 리뷰 {result['review_id']}를 찾을 수 없습니다")
```

---

## 4-3. 리뷰 배치 삭제

### 엔드포인트
```
DELETE /api/v1/vector/reviews/delete/batch
```

### 설명
여러 리뷰를 배치로 삭제합니다. (성능 최적화)

**특징:**
- 여러 리뷰를 한 번에 삭제하여 성능 향상
- 존재하지 않는 리뷰는 자동으로 건너뜀
- 10개 리뷰를 1번의 API 호출로 처리 가능

### 요청 예시
```bash
curl -X DELETE "http://localhost:8000/api/v1/vector/reviews/delete/batch" \
  -H "Content-Type: application/json" \
  -d '{
    "restaurant_id": "res_1234",
    "review_ids": ["rev_3001", "rev_3002", "rev_3003"]
  }'
```

### 응답 예시
```json
{
  "results": [
    {
      "action": "deleted",
      "review_id": "rev_3001",
      "point_id": "abc123..."
    },
    {
      "action": "deleted",
      "review_id": "rev_3002",
      "point_id": "def456..."
    },
    {
      "action": "not_found",
      "review_id": "rev_3003",
      "point_id": "ghi789..."
    }
  ],
  "total": 3,
  "deleted_count": 2,
  "not_found_count": 1
}
```

### Python 예시
```python
import requests

url = "http://localhost:8000/api/v1/vector/reviews/delete/batch"

# 10개 리뷰를 한 번에 삭제
data = {
    "restaurant_id": "res_1234",
    "review_ids": [f"rev_{i:04d}" for i in range(1, 11)]  # 10개 리뷰
}

response = requests.delete(url, json=data)
result = response.json()

print(f"✅ 총 {result['total']}개 리뷰 처리")
print(f"✅ 삭제: {result['deleted_count']}개")
print(f"⚠️ 미발견: {result['not_found_count']}개")

# 각 리뷰 결과 확인
for r in result["results"]:
    if r["action"] == "deleted":
        print(f"  ✅ {r['review_id']}: 삭제됨")
    else:
        print(f"  ⚠️ {r['review_id']}: 찾을 수 없음")
```

**성능 비교:**
- **개별 삭제**: 10개 리뷰 = 10번 API 호출 + 10번 Qdrant delete
- **배치 삭제**: 10개 리뷰 = 1번 API 호출 + 1번 배치 Qdrant delete

---

## 5. 이미지 리뷰 검색 (벡터 검색)

### 엔드포인트
```
POST /api/v1/vector/search/with-images
```

### 요청 예시
```bash
curl -X POST "http://localhost:8000/api/v1/vector/search/with-images" \
  -H "Content-Type: application/json" \
  -d '{
    "query_text": "맛있다",
    "limit": 10,
    "min_score": 0.0
  }'
```

### 응답 예시
```json
{
  "results": [
    {
      "payload": {
        "restaurant_id": "res_1234",
        "restaurant_name": "비즐",
        "review_id": "rev_3001",
        "review": "맛있어요!",
        "image_urls": ["http://localhost:8000/image1.jpeg"]
      },
      "score": 0.85,
      "image_urls": ["http://localhost:8000/image1.jpeg"]
    }
  ],
  "total": 1
}
```

### Python 예시
```python
import requests

url = "http://localhost:8000/api/v1/vector/search/with-images"
data = {
    "query_text": "맛있다",
    "limit": 10
}

response = requests.post(url, json=data)
result = response.json()

for item in result["results"]:
    print(f"리뷰: {item['payload']['review']}")
    print(f"이미지: {item['image_urls']}")
```

---

## 6. 벡터 데이터 업로드

### 엔드포인트
```
POST /api/v1/vector/upload
```

### 설명
레스토랑 데이터를 벡터 데이터베이스에 업로드합니다. (최초 1회)

### 요청 예시
```bash
curl -X POST "http://localhost:8000/api/v1/vector/upload" \
  -H "Content-Type: application/json" \
  -d '{
    "data": {
      "restaurants": [
        {
          "restaurant_id": "res_1234",
          "restaurant_name": "비즐",
          "reviews": [
            {
              "review_id": "rev_3001",
              "user_id": "user_2001",
              "datetime": "2026-01-03 12:10:00",
              "group": "카카오",
              "review": "점심시간이라 사람이 많았지만 생각보다 빨리 나왔다.",
              "images": {"url": "http://localhost:8000/bizzle_image1.jpeg"}
            }
          ]
        }
      ]
    }
  }'
```

### 응답 예시
```json
{
  "points_count": 1,
  "collection_name": "reviews_collection"
}
```

### Python 예시
```python
import requests

url = "http://localhost:8000/api/v1/vector/upload"
data = {
    "data": {
        "restaurants": [
            {
                "restaurant_id": "res_1234",
                "restaurant_name": "비즐",
                "reviews": [
                    {
                        "review_id": "rev_3001",
                        "review": "맛있어요!",
                        "user_id": "user_123",
                        "datetime": "2024-01-01T12:00:00",
                        "group": "group_1"
                    }
                ]
            }
        ]
    }
}

response = requests.post(url, json=data)
result = response.json()
print(f"✅ 업로드 완료: {result['points_count']}개 포인트")
```

---

## 7. 의미 기반 리뷰 검색 (벡터 검색)

### 엔드포인트
```
POST /api/v1/vector/search/similar
```

### 설명
의미 기반으로 유사한 리뷰를 검색합니다.

### 요청 예시
```bash
curl -X POST "http://localhost:8000/api/v1/vector/search/similar" \
  -H "Content-Type: application/json" \
  -d '{
    "query_text": "맛있다",
    "restaurant_id": "res_1234",
    "limit": 3,
    "min_score": 0.0
  }'
```

### 응답 예시
```json
{
  "results": [
    {
      "payload": {
        "restaurant_id": "res_1234",
        "restaurant_name": "비즐",
        "review_id": "rev_3001",
        "review": "맛있어요!",
        "user_id": "user_2001",
        "datetime": "2026-01-03 12:10:00",
        "group": "카카오",
        "image_urls": []
      },
      "score": 0.85
    }
  ],
  "total": 1
}
```

### Python 예시
```python
import requests

url = "http://localhost:8000/api/v1/vector/search/similar"
data = {
    "query_text": "맛있다",
    "restaurant_id": "res_1234",  # 선택사항, None이면 전체 검색
    "limit": 3,
    "min_score": 0.0
}

response = requests.post(url, json=data)
result = response.json()

for item in result["results"]:
    print(f"리뷰: {item['payload']['review']}")
    print(f"점수: {item['score']}")
```

---

## 8. 레스토랑 리뷰 조회

### 엔드포인트
```
GET /api/v1/vector/restaurants/{restaurant_id}/reviews
```

### 설명
레스토랑 ID로 해당 레스토랑의 모든 리뷰를 조회합니다.

### 요청 예시
```bash
curl -X GET "http://localhost:8000/api/v1/vector/restaurants/res_1234/reviews"
```

### 응답 예시
```json
{
  "restaurant_id": "res_1234",
  "reviews": [
    {
      "restaurant_id": "res_1234",
      "restaurant_name": "비즐",
      "review_id": "rev_3001",
      "user_id": "user_2001",
      "datetime": "2026-01-03 12:10:00",
      "group": "카카오",
      "review": "점심시간이라 사람이 많았지만 생각보다 빨리 나왔다.",
      "image_urls": ["http://localhost:8000/bizzle_image1.jpeg"]
    }
  ],
  "total": 1
}
```

### Python 예시
```python
import requests

url = "http://localhost:8000/api/v1/vector/restaurants/res_1234/reviews"
response = requests.get(url)
result = response.json()

print(f"✅ 레스토랑 {result['restaurant_id']}: {result['total']}개 리뷰")
for review in result["reviews"]:
    print(f"  - {review['review'][:50]}...")
```

---

## 9. 레스토랑 이름으로 리뷰 조회

### 엔드포인트
```
GET /api/v1/restaurants/{restaurant_name}/reviews
```

### 설명
레스토랑 이름으로 해당 레스토랑의 리뷰를 조회합니다.

### 요청 예시
```bash
curl -X GET "http://localhost:8000/api/v1/restaurants/비즐/reviews"
```

### 응답 예시
```json
{
  "restaurant_name": "비즐",
  "restaurant_id": "res_1234",
  "reviews": ["리뷰1", "리뷰2", ...],
  "total": 2
}
```

### Python 예시
```python
import requests

url = "http://localhost:8000/api/v1/restaurants/비즐/reviews"
response = requests.get(url)
result = response.json()

print(f"✅ {result['restaurant_name']}: {result['total']}개 리뷰")
```

---

## 전체 워크플로우 예시

주요 기능들을 순차적으로 사용하는 예시:

```python
import requests

BASE_URL = "http://localhost:8000"
RESTAURANT_ID = "res_1234"

# 0. 벡터 데이터 업로드 (최초 1회)
data = {
    "restaurants": [
        {
            "restaurant_id": RESTAURANT_ID,
            "restaurant_name": "비즐",
            "reviews": [
                {
                    "review_id": "rev_3001",
                    "user_id": "user_2001",
                    "datetime": "2026-01-03 12:10:00",
                    "group": "카카오",
                    "review": "점심시간이라 사람이 많았지만 생각보다 빨리 나왔다.",
                    "images": {"url": "http://localhost:8000/bizzle_image1.jpeg"}
                },
                # ... 더 많은 리뷰
            ]
        }
    ]
}

upload_response = requests.post(
    f"{BASE_URL}/api/v1/vector/upload",
    json={"data": data}
)
print(f"✅ 데이터 업로드: {upload_response.json()['points_count']}개")

# 1. 감성 비율 추출
reviews = [
    "점심시간이라 사람이 많았지만 생각보다 빨리 나왔다.",
    "가츠동은 괜찮았는데 다른 메뉴는 좀 애매했다.",
    "직원 응대가 그날그날 다른 느낌이다.",
    "음식은 맛있을 때도 있지만 오늘은 좀 짰다.",
    "웨이팅이 길 줄 알았는데 회전이 빨라서 괜찮았다."
]

sentiment_response = requests.post(
    f"{BASE_URL}/api/v1/sentiment/analyze",
    json={
        "reviews": reviews,
        "restaurant_name": "비즐",
        "restaurant_id": RESTAURANT_ID
    }
)
sentiment_result = sentiment_response.json()

print(f"✅ 감성 비율: 긍정 {sentiment_result['positive_ratio']}%, 부정 {sentiment_result['negative_ratio']}%")

# 2. 리뷰 요약 (벡터 검색 활용 - 자동으로 긍정/부정 리뷰 검색)
summarize_response = requests.post(
    f"{BASE_URL}/api/v1/llm/summarize",
    json={
        "restaurant_id": RESTAURANT_ID,
        "positive_query": "맛있다 좋다 만족",
        "negative_query": "맛없다 별로 불만",
        "limit": 10
    }
)
summarize_result = summarize_response.json()

print(f"✅ 요약: {summarize_result['overall_summary']}")
print(f"✅ 긍정 리뷰 {summarize_result['positive_count']}개, 부정 리뷰 {summarize_result['negative_count']}개")
print(f"✅ 메타데이터 포함: {len(summarize_result['positive_reviews'])}개 긍정 리뷰")

# 3. 강점 추출 (벡터 검색 활용 - 자동으로 비교 대상 검색)
strengths_response = requests.post(
    f"{BASE_URL}/api/v1/llm/extract/strengths",
    json={
        "target_restaurant_id": RESTAURANT_ID,
        "comparison_restaurant_ids": ["res_1235"],  # None이면 타겟 제외한 모든 레스토랑과 자동 비교
        "query": "맛있다 좋다 만족",
        "limit": 5
    }
)
strengths_result = strengths_response.json()

print(f"✅ 강점: {strengths_result['strength_summary']}")
print(f"✅ 타겟 리뷰 {strengths_result['target_count']}개, 비교 리뷰 {strengths_result['comparison_count']}개")

# 4. 리뷰 Upsert (포인트 업데이트)
# 4-1. 개별 upsert (낙관적 잠금 필요 시)
upsert_response = requests.post(
    f"{BASE_URL}/api/v1/vector/reviews/upsert",
    json={
        "restaurant_id": RESTAURANT_ID,
        "restaurant_name": "비즐",
        "review": {
            "review_id": "rev_3001",
            "review": "맛있어요!",
            "user_id": "user_123",
            "datetime": "2024-01-01T12:00:00",
            "group": "group_1",
            "version": 1
        },
        "update_version": None  # 중복 방지
    }
)
upsert_result = upsert_response.json()
print(f"✅ 리뷰 {upsert_result['action']}: 버전 {upsert_result['version']}")

# 4-2. 배치 upsert (10개 리뷰 한 번에 처리)
batch_upsert_response = requests.post(
    f"{BASE_URL}/api/v1/vector/reviews/upsert/batch",
    json={
        "restaurant_id": RESTAURANT_ID,
        "restaurant_name": "비즐",
        "reviews": [
            {
                "review_id": f"rev_{i:04d}",
                "review": f"리뷰 내용 {i}",
                "user_id": f"user_{i}",
                "datetime": "2024-01-01T12:00:00",
                "group": "group_1",
                "version": 1
            }
            for i in range(1, 11)  # 10개 리뷰
        ],
        "batch_size": 32
    }
)
batch_upsert_result = batch_upsert_response.json()
print(f"✅ 배치 upsert: {batch_upsert_result['success_count']}/{batch_upsert_result['total']}개 성공")

# 4-3. 리뷰 삭제
delete_response = requests.delete(
    f"{BASE_URL}/api/v1/vector/reviews/delete",
    json={
        "restaurant_id": RESTAURANT_ID,
        "review_id": "rev_3001"
    }
)
delete_result = delete_response.json()
print(f"✅ 리뷰 삭제: {delete_result['action']}")

# 4-4. 리뷰 배치 삭제
batch_delete_response = requests.delete(
    f"{BASE_URL}/api/v1/vector/reviews/delete/batch",
    json={
        "restaurant_id": RESTAURANT_ID,
        "review_ids": ["rev_3002", "rev_3003"]
    }
)
batch_delete_result = batch_delete_response.json()
print(f"✅ 배치 삭제: {batch_delete_result['deleted_count']}/{batch_delete_result['total']}개 삭제")

# 5. 이미지가 있는 리뷰 검색 (벡터 검색)
images_response = requests.post(
    f"{BASE_URL}/api/v1/vector/search/with-images",
    json={
        "query_text": "맛있다",
        "limit": 10
    }
)
images_result = images_response.json()

print(f"✅ 이미지 리뷰 {images_result['total']}개 발견")
for result in images_result['results']:
    print(f"  - 리뷰: {result['payload']['review'][:50]}...")
    print(f"    이미지: {result['image_urls']}")
    print(f"    메타데이터: {result['payload']['restaurant_name']}, {result['payload']['datetime']}")
```

---

## API 문서

실행 중인 서버에서 다음 URL로 상세한 API 문서를 확인할 수 있습니다:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

