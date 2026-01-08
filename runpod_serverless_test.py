#!/usr/bin/env python3
"""
RUNPOD Serverless Endpoint 테스트 스크립트

RUNPOD Serverless Endpoint에 요청을 보내고 결과를 받는 테스트 스크립트입니다.

사용 방법:
1. 환경 변수 설정:
   export RUNPOD_API_KEY='your-api-key'
   export RUNPOD_ENDPOINT_ID='your-endpoint-id'

2. 실행:
   python runpod_serverless_test.py

주의사항:
- handler 구조에 따라 input_data 형식이 달라질 수 있습니다
- 현재는 handler에 직접 데이터를 전달하는 형태로 작성되었습니다
- 만약 handler가 HTTP 요청을 래핑하는 형태라면 주석 처리된 형식을 사용하세요
"""

import requests
import json
import time
import os
from typing import Dict, Any, Optional

# RUNPOD Serverless 설정
RUNPOD_API_KEY = os.getenv("RUNPOD_API_KEY", "YOUR_RUNPOD_API_KEY")  # 환경 변수에서 가져오기
ENDPOINT_ID = os.getenv("RUNPOD_ENDPOINT_ID", "YOUR_ENDPOINT_ID")  # 환경 변수에서 가져오기

# RUNPOD API Base URL
RUNPOD_API_BASE = "https://api.runpod.ai/v2"
RUNPOD_RUN_URL = f"{RUNPOD_API_BASE}/{ENDPOINT_ID}/run"
RUNPOD_STATUS_URL = f"{RUNPOD_API_BASE}/{ENDPOINT_ID}/status"
RUNPOD_STREAM_URL = f"{RUNPOD_API_BASE}/{ENDPOINT_ID}/stream"

# 헤더 설정
HEADERS = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {RUNPOD_API_KEY}"
}


def submit_job(input_data: Dict[str, Any], timeout: int = 30) -> Optional[str]:
    """
    RUNPOD Serverless에 job 제출
    
    Args:
        input_data: API에 전달할 입력 데이터
        timeout: 타임아웃 (초)
        
    Returns:
        job_id (성공 시) 또는 None (실패 시)
    """
    try:
        payload = {
            "input": input_data
        }
        
        print(f"   📤 Job 제출 중...")
        response = requests.post(
            RUNPOD_RUN_URL,
            headers=HEADERS,
            json=payload,
            timeout=timeout
        )
        
        response.raise_for_status()
        result = response.json()
        
        if "id" in result:
            job_id = result["id"]
            print(f"   ✅ Job 제출 성공: {job_id}")
            return job_id
        else:
            print(f"   ❌ Job ID를 받지 못했습니다: {result}")
            return None
            
    except requests.exceptions.HTTPError as e:
        print(f"   ❌ HTTP 오류: {e}")
        print(f"   응답: {response.text[:500]}")
        return None
    except Exception as e:
        print(f"   ❌ Job 제출 실패: {e}")
        return None


def get_job_status(job_id: str, timeout: int = 10) -> Optional[Dict[str, Any]]:
    """
    Job 상태 조회
    
    Args:
        job_id: 조회할 job ID
        timeout: 타임아웃 (초)
        
    Returns:
        job 상태 딕셔너리 또는 None
    """
    try:
        response = requests.get(
            f"{RUNPOD_STATUS_URL}/{job_id}",
            headers=HEADERS,
            timeout=timeout
        )
        
        response.raise_for_status()
        return response.json()
        
    except Exception as e:
        print(f"   ❌ 상태 조회 실패: {e}")
        return None


def wait_for_job_completion(
    job_id: str,
    max_wait_time: int = 300,
    poll_interval: int = 2,
    verbose: bool = True
) -> Optional[Dict[str, Any]]:
    """
    Job 완료 대기 및 결과 반환
    
    Args:
        job_id: 대기할 job ID
        max_wait_time: 최대 대기 시간 (초)
        poll_interval: 상태 조회 간격 (초)
        verbose: 상세 로그 출력 여부
        
    Returns:
        완료된 job 결과 또는 None
    """
    start_time = time.time()
    last_status = None
    
    if verbose:
        print(f"   ⏳ Job 완료 대기 중... (최대 {max_wait_time}초)")
    
    while True:
        elapsed_time = time.time() - start_time
        
        if elapsed_time > max_wait_time:
            print(f"   ❌ 타임아웃: {max_wait_time}초 초과")
            return None
        
        status = get_job_status(job_id)
        
        if not status:
            if verbose:
                print(f"   ⚠️ 상태 조회 실패, 재시도 중... ({elapsed_time:.1f}초)")
            time.sleep(poll_interval)
            continue
        
        job_status = status.get("status", "UNKNOWN")
        
        # 상태가 변경되었을 때만 출력
        if job_status != last_status:
            if verbose:
                print(f"   📊 상태: {job_status} ({elapsed_time:.1f}초 경과)")
            last_status = job_status
        
        if job_status == "COMPLETED":
            if verbose:
                print(f"   ✅ Job 완료! (소요 시간: {elapsed_time:.1f}초)")
            return status.get("output")
        elif job_status == "FAILED":
            error = status.get("error", "알 수 없는 오류")
            print(f"   ❌ Job 실패: {error}")
            return None
        elif job_status in ["IN_QUEUE", "IN_PROGRESS"]:
            # 계속 대기
            time.sleep(poll_interval)
        else:
            print(f"   ⚠️ 알 수 없는 상태: {job_status}")
            time.sleep(poll_interval)


def test_sentiment_analysis():
    """감성 분석 테스트"""
    print("\n" + "=" * 60)
    print("[테스트 1] 감성 분석")
    print("=" * 60)
    
    # handler.py는 endpoint, method, data 형식을 사용합니다
    input_data = {
        "endpoint": "/api/v1/sentiment/analyze",
        "method": "POST",
        "data": {
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
        }
    }
    
    job_id = submit_job(input_data)
    if not job_id:
        return None
    
    result = wait_for_job_completion(job_id, max_wait_time=120)
    
    if result:
        # handler 응답 형식: {"status": "success", "data": {...}}
        if result.get("status") == "success":
            data = result.get("data", {})
            print(f"\n   ✅ 감성 분석 결과:")
            print(f"      레스토랑: {data.get('restaurant_name', 'N/A')}")
            print(f"      긍정 비율: {data.get('positive_ratio', 0)}%")
            print(f"      부정 비율: {data.get('negative_ratio', 0)}%")
            print(f"      총 리뷰: {data.get('total_count', 0)}개")
            return data
        else:
            print(f"   ❌ 감성 분석 실패: {result.get('error', '알 수 없는 오류')}")
            return None
    else:
        print("   ❌ 감성 분석 실패")
        return None


def test_vector_upload():
    """벡터 데이터 업로드 테스트"""
    print("\n" + "=" * 60)
    print("[테스트 2] 벡터 데이터 업로드")
    print("=" * 60)
    
    test_data = {
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
                            "review": "점심시간이라 사람이 많았지만 생각보다 빨리 나왔다. 맛도 정말 좋아요!",
                            "version": 1
                        },
                        {
                            "review_id": "rev_3002",
                            "user_id": "user_2002",
                            "datetime": "2026-01-03 12:12:00",
                            "group": "네이버",
                            "review": "가츠동이 정말 맛있고 가격도 합리적이에요. 직원들도 친절합니다.",
                            "version": 1
                        }
                    ]
                },
                {
                    "restaurant_id": "res_1235",
                    "restaurant_name": "시올돈",
                    "reviews": [
                        {
                            "review_id": "rev_4001",
                            "user_id": "user_2101",
                            "datetime": "2026-02-03 18:00:00",
                            "group": "카카오",
                            "review": "음식 맛은 무난하고 실패는 없는 편이다.",
                            "version": 1
                        }
                    ]
                }
            ]
        }
    }
    
    # handler.py는 endpoint, method, data 형식을 사용합니다
    input_data = {
        "endpoint": "/api/v1/vector/upload",
        "method": "POST",
        "data": test_data
    }
    
    job_id = submit_job(input_data)
    if not job_id:
        return None
    
    result = wait_for_job_completion(job_id, max_wait_time=180)
    
    if result:
        # handler 응답 형식: {"status": "success", "data": {...}}
        if result.get("status") == "success":
            data = result.get("data", {})
            print(f"\n   ✅ 업로드 완료:")
            print(f"      포인트 수: {data.get('points_count', 0)}개")
            print(f"      컬렉션: {data.get('collection_name', 'N/A')}")
            return data
        else:
            print(f"   ❌ 업로드 실패: {result.get('error', '알 수 없는 오류')}")
            return None
    else:
        print("   ❌ 업로드 실패")
        return None


def test_vector_search():
    """벡터 검색 테스트"""
    print("\n" + "=" * 60)
    print("[테스트 3] 벡터 검색")
    print("=" * 60)
    
    # handler.py는 endpoint, method, data 형식을 사용합니다
    input_data = {
        "endpoint": "/api/v1/vector/search/similar",
        "method": "POST",
        "data": {
            "query_text": "맛있다",
            "limit": 3,
            "min_score": 0.0
        }
    }
    
    job_id = submit_job(input_data)
    if not job_id:
        return None
    
    result = wait_for_job_completion(job_id, max_wait_time=60)
    
    if result:
        # handler 응답 형식: {"status": "success", "data": {...}}
        if result.get("status") == "success":
            data = result.get("data", {})
            total = data.get("total", 0)
            print(f"\n   ✅ 검색 결과: {total}개 발견")
            if total > 0:
                results = data.get("results", [])
                for idx, item in enumerate(results[:3], 1):
                    print(f"      {idx}. {item.get('payload', {}).get('review', '')[:50]}...")
            return data
        else:
            print(f"   ❌ 검색 실패: {result.get('error', '알 수 없는 오류')}")
            return None
    else:
        print("   ❌ 검색 실패")
        return None


def test_summarize():
    """리뷰 요약 테스트"""
    print("\n" + "=" * 60)
    print("[테스트 4] 리뷰 요약")
    print("=" * 60)
    
    # handler.py는 endpoint, method, data 형식을 사용합니다
    input_data = {
        "endpoint": "/api/v1/llm/summarize",
        "method": "POST",
        "data": {
            "restaurant_id": "res_1234",
            "positive_query": "맛있다 좋다 만족",
            "negative_query": "맛없다 별로 불만",
            "limit": 10,
            "min_score": 0.0
        }
    }
    
    job_id = submit_job(input_data)
    if not job_id:
        return None
    
    result = wait_for_job_completion(job_id, max_wait_time=180)
    
    if result:
        # handler 응답 형식: {"status": "success", "data": {...}}
        if result.get("status") == "success":
            data = result.get("data", {})
            print(f"\n   ✅ 요약 완료:")
            print(f"      긍정 리뷰: {data.get('positive_count', 0)}개")
            print(f"      부정 리뷰: {data.get('negative_count', 0)}개")
            print(f"      전체 요약: {data.get('overall_summary', '')[:100]}...")
            return data
        else:
            print(f"   ❌ 요약 실패: {result.get('error', '알 수 없는 오류')}")
            return None
    else:
        print("   ❌ 요약 실패")
        return None


def test_extract_strengths():
    """강점 추출 테스트"""
    print("\n" + "=" * 60)
    print("[테스트 5] 강점 추출")
    print("=" * 60)
    
    # handler.py는 endpoint, method, data 형식을 사용합니다
    input_data = {
        "endpoint": "/api/v1/llm/extract/strengths",
        "method": "POST",
        "data": {
            "target_restaurant_id": "res_1234",
            "comparison_restaurant_ids": ["res_1235"],
            "query": "맛있다 좋다 만족",
            "limit": 5,
            "min_score": 0.0
        }
    }
    
    job_id = submit_job(input_data)
    if not job_id:
        return None
    
    result = wait_for_job_completion(job_id, max_wait_time=180)
    
    if result:
        # handler 응답 형식: {"status": "success", "data": {...}}
        if result.get("status") == "success":
            data = result.get("data", {})
            print(f"\n   ✅ 강점 추출 완료:")
            print(f"      강점: {data.get('strength_summary', '')[:150]}...")
            print(f"      타겟 리뷰: {data.get('target_count', 0)}개")
            print(f"      비교 리뷰: {data.get('comparison_count', 0)}개")
            return data
        else:
            print(f"   ❌ 강점 추출 실패: {result.get('error', '알 수 없는 오류')}")
            return None
    else:
        print("   ❌ 강점 추출 실패")
        return None


def test_all():
    """모든 테스트 실행"""
    print("=" * 60)
    print("RUNPOD Serverless Endpoint 테스트")
    print("=" * 60)
    print(f"Endpoint ID: {ENDPOINT_ID}")
    print(f"API Key: {'*' * 20 if RUNPOD_API_KEY != 'YOUR_RUNPOD_API_KEY' else '설정 필요'}")
    print("=" * 60)
    
    # 설정 확인
    if RUNPOD_API_KEY == "YOUR_RUNPOD_API_KEY" or ENDPOINT_ID == "YOUR_ENDPOINT_ID":
        print("\n⚠️ 경고: RUNPOD_API_KEY 또는 RUNPOD_ENDPOINT_ID가 설정되지 않았습니다.")
        print("   환경 변수로 설정하거나 스크립트 내에서 직접 설정하세요.")
        print("   예: export RUNPOD_API_KEY='your-api-key'")
        print("   예: export RUNPOD_ENDPOINT_ID='your-endpoint-id'")
        print("\n💡 RUNPOD Serverless Handler 구조:")
        print("   - handler.py는 endpoint, method, data 형식을 사용합니다")
        print("   - 예: {'endpoint': '/api/v1/...', 'method': 'POST', 'data': {...}}")
        return
    
    results = {}
    
    # 1. 감성 분석
    results["sentiment"] = test_sentiment_analysis()
    
    # 2. 벡터 데이터 업로드
    results["upload"] = test_vector_upload()
    
    # 3. 벡터 검색 (업로드 후)
    if results["upload"]:
        results["search"] = test_vector_search()
    else:
        print("\n   ⚠️ 벡터 검색 스킵: 데이터 업로드 실패")
        results["search"] = None
    
    # 4. 리뷰 요약 (업로드 후)
    if results["upload"]:
        results["summarize"] = test_summarize()
    else:
        print("\n   ⚠️ 리뷰 요약 스킵: 데이터 업로드 실패")
        results["summarize"] = None
    
    # 5. 강점 추출 (업로드 후)
    if results["upload"]:
        results["strengths"] = test_extract_strengths()
    else:
        print("\n   ⚠️ 강점 추출 스킵: 데이터 업로드 실패")
        results["strengths"] = None
    
    # 결과 요약
    print("\n" + "=" * 60)
    print("테스트 결과 요약")
    print("=" * 60)
    for test_name, result in results.items():
        status = "✅ 성공" if result else "❌ 실패"
        print(f"   {test_name}: {status}")
    
    print("\n" + "=" * 60)
    print("테스트 완료!")
    print("=" * 60)


if __name__ == "__main__":
    test_all()

