"""
리뷰 데이터 처리 유틸리티 모듈
"""

from typing import Dict, List, Tuple, Union, Optional


def get_review_list(data: Dict, restaurant_name: str) -> Tuple[List[str], str]:
    """
    레스토랑 이름으로 리뷰 리스트와 레스토랑 ID를 반환합니다.
    
    Args:
        data: 레스토랑 데이터 딕셔너리
        restaurant_name: 레스토랑 이름
        
    Returns:
        tuple: (리뷰 리스트, 레스토랑 ID)
        
    Raises:
        ValueError: 레스토랑을 찾을 수 없는 경우
    """
    review_list = []
    restaurant_id = None
    
    for restaurant in data.get("restaurants", []):
        if restaurant.get("restaurant_name") == restaurant_name:
            restaurant_id = restaurant.get("restaurant_id")
            for review in restaurant.get("reviews", []):
                if "review" in review:
                    review_list.append(review["review"])
            break
    
    if restaurant_id is None:
        raise ValueError(f"레스토랑 '{restaurant_name}'을(를) 찾을 수 없습니다.")
    
    return review_list, restaurant_id


def extract_reviews_from_payloads(payloads: List[Dict]) -> List[str]:
    """
    payload 리스트에서 리뷰 텍스트만 추출합니다.
    
    Args:
        payloads: payload 딕셔너리 리스트
        
    Returns:
        리뷰 텍스트 리스트
    """
    return [p.get("review", "") for p in payloads if p.get("review")]


def extract_image_urls(images: Union[Dict, List, None]) -> List[str]:
    """
    images 필드에서 URL 리스트를 안전하게 추출합니다.
    
    Args:
        images: dict, list, 또는 None
        
    Returns:
        이미지 URL 리스트
    """
    image_urls = []
    
    if isinstance(images, dict):
        url = images.get("url")
        if url:
            image_urls.append(url)
    elif isinstance(images, list):
        for img in images:
            if isinstance(img, dict) and img.get("url"):
                image_urls.append(img["url"])
            elif isinstance(img, str):
                image_urls.append(img)
    
    return image_urls


def validate_review_data(review: Dict) -> bool:
    """
    리뷰 데이터의 유효성을 검증합니다.
    
    Args:
        review: 리뷰 딕셔너리
        
    Returns:
        유효성 여부
    """
    required_fields = ["review_id", "review"]
    return all(field in review for field in required_fields)


def validate_restaurant_data(restaurant: Dict) -> bool:
    """
    레스토랑 데이터의 유효성을 검증합니다.
    
    Args:
        restaurant: 레스토랑 딕셔너리
        
    Returns:
        유효성 여부
    """
    required_fields = ["restaurant_id", "restaurant_name", "reviews"]
    if not all(field in restaurant for field in required_fields):
        return False
    
    if not isinstance(restaurant.get("reviews"), list):
        return False
    
    return True

