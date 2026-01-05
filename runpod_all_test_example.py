#!/usr/bin/env python3
"""
RUNPOD 서버 API 전체 테스트 스크립트
"""

import requests
import json
import time

# RUNPOD 서버 URL 설정
BASE_URL = "https://aths8e5kzyot8c-8001.proxy.runpod.net"  # 실제 RUNPOD IP로 변경

def test_all():
    """모든 API 테스트"""
    
    print("=" * 60)
    print("RUNPOD API 테스트 시작")
    print("=" * 60)
    
    # 1. 헬스 체크
    print("\n[1/6] 헬스 체크...")
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=10)
        print(f"✅ 서버 상태: {response.json()}")
    except Exception as e:
        print(f"❌ 헬스 체크 실패: {e}")
        return
    
    # 2. 감성 분석
    print("\n[2/6] 감성 분석 테스트...")
    try:
        response = requests.post(
            f"{BASE_URL}/api/v1/sentiment/analyze",
            json={
                "reviews": ["맛있어요!", "별로에요"],
                "restaurant_name": "테스트",
                "restaurant_id": "test_001"
            },
            timeout=60
        )
        result = response.json()
        print(f"✅ 긍정: {result['positive_ratio']}%, 부정: {result['negative_ratio']}%")
    except Exception as e:
        print(f"❌ 감성 분석 실패: {e}")
    
    # 3. 벡터 데이터 업로드
    print("\n[3/6] 벡터 데이터 업로드...")
    try:
        response = requests.post(
            f"{BASE_URL}/api/v1/vector/upload",
            json={
                "data": {
                    "restaurants": [{
                        "restaurant_id": "res_test",
                        "restaurant_name": "테스트 레스토랑",
                        "reviews": [{
                            "review_id": "rev_test",
                            "user_id": "user_test",
                            "datetime": "2026-01-01 12:00:00",
                            "group": "테스트",
                            "review": "맛있어요!",
                            "version": 1
                        }]
                    }]
                }
            },
            timeout=120
        )
        result = response.json()
        print(f"✅ 업로드 완료: {result['points_count']}개 포인트")
    except Exception as e:
        print(f"❌ 업로드 실패: {e}")
    
    # 4. 벡터 검색
    print("\n[4/6] 벡터 검색 테스트...")
    try:
        response = requests.post(
            f"{BASE_URL}/api/v1/vector/search/similar",
            json={
                "query_text": "맛있다",
                "limit": 3
            },
            timeout=30
        )
        result = response.json()
        print(f"✅ 검색 결과: {result['total']}개 발견")
    except Exception as e:
        print(f"❌ 검색 실패: {e}")
    
    # 5. 리뷰 요약
    print("\n[5/6] 리뷰 요약 테스트...")
    try:
        response = requests.post(
            f"{BASE_URL}/api/v1/llm/summarize",
            json={
                "restaurant_id": "res_test",
                "positive_query": "맛있다",
                "negative_query": "맛없다",
                "limit": 5
            },
            timeout=120
        )
        result = response.json()
        print(f"✅ 요약 완료: 긍정 {result['positive_count']}개, 부정 {result['negative_count']}개")
    except Exception as e:
        print(f"❌ 요약 실패: {e}")
    
    # 6. 강점 추출
    print("\n[6/6] 강점 추출 테스트...")
    try:
        response = requests.post(
            f"{BASE_URL}/api/v1/llm/extract/strengths",
            json={
                "target_restaurant_id": "res_test",
                "query": "맛있다",
                "limit": 5
            },
            timeout=120
        )
        result = response.json()
        print(f"✅ 강점 추출 완료")
        print(f"   강점: {result['strength_summary'][:100]}...")
    except Exception as e:
        print(f"❌ 강점 추출 실패: {e}")
    
    print("\n" + "=" * 60)
    print("테스트 완료!")
    print("=" * 60)

if __name__ == "__main__":
    test_all()