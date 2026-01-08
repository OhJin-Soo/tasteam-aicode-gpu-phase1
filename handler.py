"""
RUNPOD Serverless Handler

RUNPOD Serverless Endpoint에서 사용하는 실제 handler 함수입니다.
FastAPI 앱을 직접 호출하는 방식으로 구현되었습니다.
"""

import os
import logging
from typing import Dict, Any, Optional
from fastapi.testclient import TestClient

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# FastAPI 앱 임포트 (지연 로딩으로 cold start 최적화)
_app: Optional[TestClient] = None


def get_app_client() -> TestClient:
    """FastAPI 앱 클라이언트를 싱글톤으로 관리 (cold start 최적화)"""
    global _app
    
    if _app is None:
        logger.info("FastAPI 앱 초기화 중...")
        from src.api.main import app
        _app = TestClient(app)
        logger.info("FastAPI 앱 초기화 완료")
    
    return _app


def handler(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    RUNPOD Serverless 표준 handler 함수
    
    RUNPOD serverless endpoint에서 자동으로 호출됩니다.
    FastAPI 앱을 직접 호출하여 요청을 처리합니다.
    
    Args:
        event: RUNPOD에서 전달되는 이벤트 데이터
            {
                "id": "job-id",
                "input": {
                    "endpoint": "/api/v1/sentiment/analyze",  # API 엔드포인트
                    "method": "POST",  # HTTP 메서드
                    "data": {...}  # 요청 데이터
                }
            }
    
    Returns:
        처리 결과
        {
            "status": "success" | "error",
            "status_code": 200,
            "data": {...}  # API 응답 데이터
        }
    """
    try:
        # 입력 데이터 추출
        input_data = event.get("input", {})
        
        if not input_data:
            return {
                "status": "error",
                "error": "입력 데이터가 없습니다. 'input' 필드가 필요합니다."
            }
        
        # 엔드포인트와 메서드 추출
        endpoint = input_data.get("endpoint", "/health")
        method = input_data.get("method", "GET").upper()
        data = input_data.get("data", {})
        
        logger.info(f"요청 처리: {method} {endpoint}")
        
        # FastAPI 앱 클라이언트 가져오기
        client = get_app_client()
        
        # HTTP 메서드에 따라 요청 처리
        if method == "GET":
            response = client.get(endpoint)
        elif method == "POST":
            response = client.post(endpoint, json=data)
        elif method == "PUT":
            response = client.put(endpoint, json=data)
        elif method == "DELETE":
            response = client.delete(endpoint)
        else:
            return {
                "status": "error",
                "error": f"지원하지 않는 HTTP 메서드: {method}"
            }
        
        # 응답 처리
        if response.status_code >= 200 and response.status_code < 300:
            try:
                response_data = response.json()
                return {
                    "status": "success",
                    "status_code": response.status_code,
                    "data": response_data
                }
            except Exception as e:
                # JSON이 아닌 경우 텍스트로 반환
                return {
                    "status": "success",
                    "status_code": response.status_code,
                    "data": {"text": response.text}
                }
        else:
            # HTTP 오류 처리
            try:
                error_data = response.json()
                return {
                    "status": "error",
                    "status_code": response.status_code,
                    "error": error_data.get("detail", error_data)
                }
            except:
                return {
                    "status": "error",
                    "status_code": response.status_code,
                    "error": response.text
                }
    
    except Exception as e:
        logger.error(f"Handler 오류: {str(e)}", exc_info=True)
        return {
            "status": "error",
            "error": f"Handler 실행 중 오류 발생: {str(e)}"
        }


# RUNPOD serverless가 자동으로 handler 함수를 찾습니다
# 이 파일의 handler 함수가 실행됩니다

