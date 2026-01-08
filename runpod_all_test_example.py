#!/usr/bin/env python3
"""
RUNPOD 서버 API 전체 테스트 스크립트 (강점 추출 가능한 테스트 데이터 포함)
"""

import requests
import json
import time

# RUNPOD 서버 URL 설정
BASE_URL = "http://213.192.2.68:40183"  # 실제 RUNPOD IP로 변경

def safe_json_response(response, error_msg="응답 처리 실패", allow_404=False):
    """안전하게 JSON 응답 파싱"""
    try:
        # 404는 비즈니스 로직상 정상 응답일 수 있음 (데이터 없음 등)
        if response.status_code == 404 and allow_404:
            try:
                error_detail = response.json()
                if "detail" in error_detail:
                    print(f"   ℹ️ 정보: {error_detail['detail']}")
                    return error_detail  # 404 응답도 반환
            except:
                pass
        
        response.raise_for_status()  # HTTP 오류 확인
        if not response.text:
            print(f"   ⚠️ 빈 응답 반환")
            return None
        return response.json()
    except requests.exceptions.HTTPError as e:
        # 404는 비즈니스 로직상 정상일 수 있으므로 별도 처리
        if response.status_code == 404:
            try:
                error_detail = response.json()
                if "detail" in error_detail:
                    print(f"   ℹ️ 정보: {error_detail['detail']}")
                    if allow_404:
                        return error_detail
                    else:
                        print(f"   ⚠️ 리소스를 찾을 수 없습니다 (정상일 수 있음)")
                        return None
            except:
                pass
        
        print(f"   ⚠️ HTTP 오류: {e}")
        print(f"   상태 코드: {response.status_code}")
        
        # 상세 오류 메시지 추출 시도
        try:
            error_detail = response.json()
            if "detail" in error_detail:
                print(f"   오류 상세: {error_detail['detail']}")
            else:
                print(f"   응답 내용: {json.dumps(error_detail, ensure_ascii=False, indent=2)[:500]}")
        except:
            print(f"   응답 내용 (텍스트): {response.text[:500]}")
        
        return None
    except json.JSONDecodeError as e:
        print(f"   ⚠️ JSON 파싱 오류: {e}")
        print(f"   응답 내용: {response.text[:500]}")
        print(f"   상태 코드: {response.status_code}")
        return None
    except Exception as e:
        print(f"   ⚠️ {error_msg}: {e}")
        return None

def get_test_data():
    """강점 추출이 가능한 테스트 데이터 생성"""
    return {
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
                        },
                        {
                            "review_id": "rev_3003",
                            "user_id": "user_2003",
                            "datetime": "2026-01-04 13:00:00",
                            "group": "카카오",
                            "review": "웨이팅이 길 줄 알았는데 회전이 빨라서 금방 먹을 수 있었어요. 만족합니다!",
                            "version": 1
                        },
                        {
                            "review_id": "rev_3004",
                            "user_id": "user_2004",
                            "datetime": "2026-01-05 18:30:00",
                            "group": "네이버",
                            "review": "음식이 짜긴 하지만 전체적으로는 괜찮아요.",
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
                            "review": "음식 맛은 무난하고 실패는 없는 편이다. 괜찮아요.",
                            "version": 1
                        },
                        {
                            "review_id": "rev_4002",
                            "user_id": "user_2102",
                            "datetime": "2026-02-03 18:20:00",
                            "group": "네이버",
                            "review": "웨이팅이 너무 길어서 중간에 포기할 뻔했다. 맛은 평범해요.",
                            "version": 1
                        },
                        {
                            "review_id": "rev_4003",
                            "user_id": "user_2103",
                            "datetime": "2026-02-04 19:00:00",
                            "group": "카카오",
                            "review": "직원들이 전반적으로 친절해서 인상은 좋았다.",
                            "version": 1
                        },
                        {
                            "review_id": "rev_4004",
                            "user_id": "user_2104",
                            "datetime": "2026-02-05 19:10:00",
                            "group": "네이버",
                            "review": "음식은 평타 이상인데 웨이팅 각오는 해야 한다.",
                            "version": 1
                        }
                    ]
                },
                {
                    "restaurant_id": "res_1236",
                    "restaurant_name": "돈카츠야",
                    "reviews": [
                        {
                            "review_id": "rev_5001",
                            "user_id": "user_2201",
                            "datetime": "2026-03-01 12:00:00",
                            "group": "카카오",
                            "review": "가츠가 바삭하고 맛있어요. 하지만 가격이 좀 비싸네요.",
                            "version": 1
                        },
                        {
                            "review_id": "rev_5002",
                            "user_id": "user_2202",
                            "datetime": "2026-03-02 13:00:00",
                            "group": "네이버",
                            "review": "분위기가 좋고 음식도 괜찮아요. 다만 대기 시간이 있어요.",
                            "version": 1
                        },
                        {
                            "review_id": "rev_5003",
                            "user_id": "user_2203",
                            "datetime": "2026-03-03 18:00:00",
                            "group": "카카오",
                            "review": "메뉴가 다양하고 맛도 좋습니다.",
                            "version": 1
                        }
                    ]
                }
            ]
        }
    }

def test_all():
    """모든 API 테스트"""
    
    print("=" * 60)
    print("RUNPOD API 테스트 시작")
    print(f"서버 URL: {BASE_URL}")
    print("=" * 60)
    
    # 전체 테스트 시작 시간
    total_start_time = time.time()
    
    # 1. 헬스 체크
    print("\n[1/7] 헬스 체크...")
    try:
        start_time = time.time()
        response = requests.get(f"{BASE_URL}/health", timeout=10)
        elapsed_time = time.time() - start_time
        result = safe_json_response(response, "헬스 체크 실패")
        if result:
            print(f"✅ 서버 상태: {result}")
            print(f"   ⏱️ 응답 시간: {elapsed_time:.2f}초")
        else:
            print("❌ 헬스 체크 실패: 응답을 파싱할 수 없습니다")
            return
    except Exception as e:
        print(f"❌ 헬스 체크 실패: {e}")
        return
    
    # 2. 감성 분석
    print("\n[2/7] 감성 분석 테스트...")
    try:
        start_time = time.time()
        response = requests.post(
            f"{BASE_URL}/api/v1/sentiment/analyze",
            json={
                "reviews": ["맛있어요!", "별로에요"],
                "restaurant_name": "테스트",
                "restaurant_id": "test_001"
            },
            timeout=60
        )
        elapsed_time = time.time() - start_time
        result = safe_json_response(response, "감성 분석 실패")
        if result:
            print(f"✅ 긍정: {result['positive_ratio']}%, 부정: {result['negative_ratio']}%")
            print(f"   ⏱️ 응답 시간: {elapsed_time:.2f}초")
        else:
            print("❌ 감성 분석 실패")
    except Exception as e:
        print(f"❌ 감성 분석 실패: {e}")
    
    # 3. 벡터 데이터 업로드 (강점 추출을 위한 여러 레스토랑 데이터)
    print("\n[3/7] 벡터 데이터 업로드 (강점 추출용 테스트 데이터)...")
    print("   📝 3개 레스토랑 데이터 업로드:")
    print("      - 비즐 (res_1234): 4개 리뷰")
    print("      - 시올돈 (res_1235): 4개 리뷰")
    print("      - 돈카츠야 (res_1236): 3개 리뷰")
    try:
        test_data = get_test_data()
        start_time = time.time()
        response = requests.post(
            f"{BASE_URL}/api/v1/vector/upload",
            json=test_data,
            timeout=120
        )
        elapsed_time = time.time() - start_time
        result = safe_json_response(response, "업로드 실패")
        if result:
            print(f"✅ 업로드 완료: {result['points_count']}개 포인트")
            print(f"   ⏱️ 응답 시간: {elapsed_time:.2f}초")
        else:
            print("❌ 업로드 실패")
            print("   💡 해결 방법:")
            print("   1. RUNPOD 환경 변수에 QDRANT_URL=:memory: 설정 (인메모리 사용)")
            print("   2. 또는 외부 Qdrant 서버 URL 설정")
            print("   3. 서버 로그 확인: docker logs 또는 RUNPOD 로그 뷰어")
            return  # 업로드 실패 시 이후 테스트 중단
    except Exception as e:
        print(f"❌ 업로드 실패: {e}")
        return
    
    # 4. 벡터 검색
    print("\n[4/7] 벡터 검색 테스트...")
    try:
        start_time = time.time()
        response = requests.post(
            f"{BASE_URL}/api/v1/vector/search/similar",
            json={
                "query_text": "맛있다",
                "limit": 3
            },
            timeout=30
        )
        elapsed_time = time.time() - start_time
        result = safe_json_response(response, "검색 실패", allow_404=True)
        if result:
            if "total" in result:
                print(f"✅ 검색 결과: {result['total']}개 발견")
                print(f"   ⏱️ 응답 시간: {elapsed_time:.2f}초")
            else:
                print(f"ℹ️ 검색 결과 없음 (정상일 수 있음)")
                print(f"   ⏱️ 응답 시간: {elapsed_time:.2f}초")
        else:
            print("❌ 검색 실패")
    except Exception as e:
        print(f"❌ 검색 실패: {e}")
    
    # 5. 리뷰 요약
    print("\n[5/7] 리뷰 요약 테스트 (비즐)...")
    try:
        start_time = time.time()
        response = requests.post(
            f"{BASE_URL}/api/v1/llm/summarize",
            json={
                "restaurant_id": "res_1234",
                "positive_query": "맛있다 좋다 만족",
                "negative_query": "맛없다 별로 불만",
                "limit": 5
            },
            timeout=120
        )
        elapsed_time = time.time() - start_time
        result = safe_json_response(response, "요약 실패", allow_404=True)
        if result:
            if "positive_count" in result:
                print(f"✅ 요약 완료: 긍정 {result['positive_count']}개, 부정 {result['negative_count']}개")
                print(f"   전체 요약: {result.get('overall_summary', '')[:100]}...")
                print(f"   ⏱️ 응답 시간: {elapsed_time:.2f}초")
            else:
                print(f"ℹ️ 요약할 리뷰가 없습니다 (정상일 수 있음)")
                print(f"   ⏱️ 응답 시간: {elapsed_time:.2f}초")
        else:
            print("❌ 요약 실패")
    except Exception as e:
        print(f"❌ 요약 실패: {e}")
    
    # 6. 강점 추출 (비즐 vs 시올돈, 돈카츠야)
    print("\n[6/7] 강점 추출 테스트 (비즐 vs 시올돈, 돈카츠야)...")
    print("   📝 타겟: 비즐 (res_1234)")
    print("   📝 비교 대상: 시올돈 (res_1235), 돈카츠야 (res_1236)")
    try:
        start_time = time.time()
        response = requests.post(
            f"{BASE_URL}/api/v1/llm/extract/strengths",
            json={
                "target_restaurant_id": "res_1234",
                "comparison_restaurant_ids": ["res_1235", "res_1236"],  # 비교 대상 명시
                "query": "맛있다 좋다 만족",
                "limit": 5,
                "min_score": 0.0
            },
            timeout=120
        )
        elapsed_time = time.time() - start_time
        result = safe_json_response(response, "강점 추출 실패", allow_404=True)
        if result:
            if "strength_summary" in result:
                print(f"✅ 강점 추출 완료!")
                print(f"\n   💪 강점 요약:")
                print(f"   {result['strength_summary']}")
                print(f"\n   📊 통계:")
                print(f"   - 타겟 리뷰: {result.get('target_count', 0)}개")
                print(f"   - 비교 리뷰: {result.get('comparison_count', 0)}개")
                print(f"   ⏱️ 응답 시간: {elapsed_time:.2f}초")
            else:
                print(f"ℹ️ {result.get('detail', '강점 추출할 데이터가 없습니다')}")
                print(f"   ⏱️ 응답 시간: {elapsed_time:.2f}초")
        else:
            print("❌ 강점 추출 실패")
    except Exception as e:
        print(f"❌ 강점 추출 실패: {e}")
    
    # 7. 강점 추출 (비교 대상 자동 선택)
    print("\n[7/7] 강점 추출 테스트 (비교 대상 자동 선택)...")
    print("   📝 타겟: 비즐 (res_1234)")
    print("   📝 비교 대상: 자동 (타겟 제외한 모든 레스토랑)")
    try:
        start_time = time.time()
        response = requests.post(
            f"{BASE_URL}/api/v1/llm/extract/strengths",
            json={
                "target_restaurant_id": "res_1234",
                "comparison_restaurant_ids": None,  # None이면 자동으로 모든 레스토랑과 비교
                "query": "맛있다 좋다 만족",
                "limit": 5,
                "min_score": 0.0
            },
            timeout=120
        )
        elapsed_time = time.time() - start_time
        result = safe_json_response(response, "강점 추출 실패", allow_404=True)
        if result:
            if "strength_summary" in result:
                print(f"✅ 강점 추출 완료!")
                print(f"\n   💪 강점 요약:")
                print(f"   {result['strength_summary']}")
                print(f"\n   📊 통계:")
                print(f"   - 타겟 리뷰: {result.get('target_count', 0)}개")
                print(f"   - 비교 리뷰: {result.get('comparison_count', 0)}개")
                print(f"   ⏱️ 응답 시간: {elapsed_time:.2f}초")
            else:
                print(f"ℹ️ {result.get('detail', '강점 추출할 데이터가 없습니다')}")
                print(f"   ⏱️ 응답 시간: {elapsed_time:.2f}초")
        else:
            print("❌ 강점 추출 실패")
    except Exception as e:
        print(f"❌ 강점 추출 실패: {e}")
    
    # 전체 테스트 시간 계산
    total_elapsed_time = time.time() - total_start_time
    
    print("\n" + "=" * 60)
    print("테스트 완료!")
    print("=" * 60)
    print(f"⏱️ 전체 테스트 소요 시간: {total_elapsed_time:.2f}초 ({total_elapsed_time/60:.2f}분)")
    print("\n💡 참고사항:")
    print("   - 벡터 데이터 업로드가 성공해야 이후 테스트가 가능합니다")
    print("   - 강점 추출은 최소 2개 이상의 레스토랑 데이터가 필요합니다")
    print("   - 비교 대상 레스토랑을 지정하거나 None으로 자동 선택할 수 있습니다")

if __name__ == "__main__":
    test_all()