"""
RUNPOD Serverless Handler 예제

RUNPOD Serverless Endpoint에서 사용할 handler 함수 예제입니다.
이 파일은 참고용이며, 실제 handler 구조에 맞게 수정해야 합니다.
"""

import json
from typing import Dict, Any

# 방법 1: 직접 API 호출 (FastAPI 앱을 직접 호출)
def handler_direct(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    RUNPOD serverless handler - 직접 API 호출 방식
    
    Args:
        event: RUNPOD에서 전달되는 이벤트 데이터
            {
                "input": {
                    "reviews": [...],
                    "restaurant_name": "...",
                    "restaurant_id": "..."
                }
            }
    
    Returns:
        API 응답 결과
    """
    from src.api.main import app
    from fastapi.testclient import TestClient
    
    # 입력 데이터 추출
    input_data = event.get("input", {})
    
    # FastAPI 앱에 직접 요청
    client = TestClient(app)
    
    # 감성 분석 API 호출 예시
    response = client.post(
        "/api/v1/sentiment/analyze",
        json=input_data
    )
    
    return {
        "status": "success",
        "data": response.json()
    }


# 방법 2: HTTP 요청 래핑 (FastAPI 앱을 HTTP 서버로 실행)
def handler_http_wrapper(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    RUNPOD serverless handler - HTTP 래핑 방식
    
    Args:
        event: RUNPOD에서 전달되는 이벤트 데이터
            {
                "input": {
                    "endpoint": "/api/v1/sentiment/analyze",
                    "method": "POST",
                    "data": {...}
                }
            }
    
    Returns:
        API 응답 결과
    """
    import requests
    
    # 입력 데이터 추출
    input_data = event.get("input", {})
    endpoint = input_data.get("endpoint", "/health")
    method = input_data.get("method", "GET")
    data = input_data.get("data", {})
    
    # 로컬 서버 URL (RUNPOD serverless 환경에서)
    base_url = "http://localhost:8001"  # 또는 환경 변수에서 가져오기
    
    # HTTP 요청
    if method.upper() == "GET":
        response = requests.get(f"{base_url}{endpoint}")
    elif method.upper() == "POST":
        response = requests.post(f"{base_url}{endpoint}", json=data)
    else:
        return {
            "status": "error",
            "error": f"지원하지 않는 HTTP 메서드: {method}"
        }
    
    return {
        "status": "success",
        "status_code": response.status_code,
        "data": response.json()
    }


# 방법 3: 직접 함수 호출 (가장 효율적)
def handler_function_call(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    RUNPOD serverless handler - 직접 함수 호출 방식 (권장)
    
    Args:
        event: RUNPOD에서 전달되는 이벤트 데이터
            {
                "input": {
                    "function": "sentiment_analyze",  # 호출할 함수명
                    "params": {
                        "reviews": [...],
                        "restaurant_name": "...",
                        "restaurant_id": "..."
                    }
                }
            }
    
    Returns:
        함수 실행 결과
    """
    from src.sentiment_analysis import analyze_reviews
    from src.llm_utils import LLMUtils
    
    # 입력 데이터 추출
    input_data = event.get("input", {})
    function_name = input_data.get("function", "sentiment_analyze")
    params = input_data.get("params", {})
    
    try:
        if function_name == "sentiment_analyze":
            llm_utils = LLMUtils()
            result = analyze_reviews(
                review_list=params.get("reviews", []),
                restaurant_name=params.get("restaurant_name", ""),
                restaurant_id=params.get("restaurant_id", ""),
            )
            return {
                "status": "success",
                "data": result
            }
        else:
            return {
                "status": "error",
                "error": f"알 수 없는 함수: {function_name}"
            }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }


# RUNPOD serverless 표준 handler (실제 사용)
def handler(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    RUNPOD Serverless 표준 handler 함수
    
    이 함수는 RUNPOD serverless endpoint에서 자동으로 호출됩니다.
    실제 handler 구조에 맞게 위의 예제 중 하나를 선택하거나 수정하세요.
    
    Args:
        event: RUNPOD에서 전달되는 이벤트
            {
                "id": "job-id",
                "input": {
                    # 실제 입력 데이터
                }
            }
    
    Returns:
        처리 결과
    """
    # 방법 1: 직접 함수 호출 (권장)
    return handler_function_call(event)
    
    # 방법 2: HTTP 래핑 (FastAPI 앱이 별도로 실행 중인 경우)
    # return handler_http_wrapper(event)
    
    # 방법 3: 직접 API 호출
    # return handler_direct(event)

