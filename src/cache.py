"""
캐싱 관리 모듈 (Phase 2: Redis 캐싱 시스템)

통합 캐싱 관리자를 제공하여 LLM 응답, 감성 분석 결과, 임베딩 벡터를 캐싱합니다.
"""
import hashlib
import json
import logging
from typing import Optional, Any

logger = logging.getLogger(__name__)

# Redis 임포트 (선택적)
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logger.warning("Redis가 설치되지 않았습니다. 캐싱이 비활성화됩니다.")


class CacheManager:
    """통합 캐싱 관리자"""
    
    def __init__(
        self,
        redis_host: str = "localhost",
        redis_port: int = 6379,
        redis_db: int = 0,
        redis_password: Optional[str] = None,
    ):
        """
        Args:
            redis_host: Redis 호스트
            redis_port: Redis 포트
            redis_db: Redis 데이터베이스 번호
            redis_password: Redis 비밀번호 (선택적)
        """
        self.enabled = False
        self.redis = None
        
        if not REDIS_AVAILABLE:
            logger.warning("Redis가 설치되지 않아 캐싱이 비활성화됩니다.")
            return
        
        try:
            self.redis = redis.Redis(
                host=redis_host,
                port=redis_port,
                db=redis_db,
                password=redis_password,
                decode_responses=False,  # 바이너리 모드로 저장
                socket_connect_timeout=5,
                socket_timeout=5,
            )
            # 연결 테스트
            self.redis.ping()
            self.enabled = True
            logger.info(f"✅ Redis 연결 성공: {redis_host}:{redis_port}/{redis_db}")
        except Exception as e:
            logger.warning(f"Redis 연결 실패: {e}. 캐싱이 비활성화됩니다.")
            self.redis = None
            self.enabled = False
    
    def _get_key(self, prefix: str, content: str) -> str:
        """
        캐시 키 생성
        
        Args:
            prefix: 키 접두사 (예: "llm", "sentiment", "embedding")
            content: 캐시할 내용 (해시화됨)
            
        Returns:
            캐시 키 문자열
        """
        # 내용을 해시화하여 키 생성
        hash_content = hashlib.md5(content.encode("utf-8")).hexdigest()
        return f"{prefix}:{hash_content}"
    
    def get(self, prefix: str, content: str) -> Optional[Any]:
        """
        캐시 조회
        
        Args:
            prefix: 키 접두사
            content: 조회할 내용
            
        Returns:
            캐시된 값 (없으면 None)
        """
        if not self.enabled or self.redis is None:
            return None
        
        try:
            key = self._get_key(prefix, content)
            cached = self.redis.get(key)
            if cached:
                # JSON 디코딩
                return json.loads(cached)
        except Exception as e:
            logger.error(f"캐시 조회 실패: {e}")
        return None
    
    def set(
        self,
        prefix: str,
        content: str,
        value: Any,
        ttl: int = 3600,
    ) -> bool:
        """
        캐시 저장
        
        Args:
            prefix: 키 접두사
            content: 저장할 내용
            value: 저장할 값
            ttl: Time To Live (초 단위, 기본값: 1시간)
            
        Returns:
            저장 성공 여부
        """
        if not self.enabled or self.redis is None:
            return False
        
        try:
            key = self._get_key(prefix, content)
            # JSON 인코딩
            serialized = json.dumps(value, ensure_ascii=False)
            self.redis.setex(key, ttl, serialized)
            return True
        except Exception as e:
            logger.error(f"캐시 저장 실패: {e}")
            return False
    
    def delete(self, prefix: str, content: str) -> bool:
        """
        캐시 삭제
        
        Args:
            prefix: 키 접두사
            content: 삭제할 내용
            
        Returns:
            삭제 성공 여부
        """
        if not self.enabled or self.redis is None:
            return False
        
        try:
            key = self._get_key(prefix, content)
            self.redis.delete(key)
            return True
        except Exception as e:
            logger.error(f"캐시 삭제 실패: {e}")
            return False
    
    def clear_prefix(self, prefix: str) -> int:
        """
        특정 접두사를 가진 모든 키 삭제
        
        Args:
            prefix: 삭제할 키 접두사
            
        Returns:
            삭제된 키 개수
        """
        if not self.enabled or self.redis is None:
            return 0
        
        try:
            pattern = f"{prefix}:*"
            keys = list(self.redis.scan_iter(match=pattern))
            if keys:
                return self.redis.delete(*keys)
            return 0
        except Exception as e:
            logger.error(f"접두사 삭제 실패: {e}")
            return 0
    
    def get_stats(self) -> dict:
        """
        캐시 통계 조회
        
        Returns:
            캐시 통계 딕셔너리
        """
        if not self.enabled or self.redis is None:
            return {
                "enabled": False,
                "redis_available": False,
            }
        
        try:
            info = self.redis.info()
            return {
                "enabled": True,
                "redis_available": True,
                "connected_clients": info.get("connected_clients", 0),
                "used_memory_human": info.get("used_memory_human", "0B"),
                "keyspace_hits": info.get("keyspace_hits", 0),
                "keyspace_misses": info.get("keyspace_misses", 0),
            }
        except Exception as e:
            logger.error(f"통계 조회 실패: {e}")
            return {
                "enabled": True,
                "redis_available": True,
                "error": str(e),
            }


# 전역 캐시 매니저 인스턴스 (선택적)
_global_cache_manager: Optional[CacheManager] = None


def get_cache_manager() -> CacheManager:
    """
    전역 캐시 매니저 인스턴스를 반환합니다.
    
    Returns:
        CacheManager 인스턴스
    """
    global _global_cache_manager
    
    if _global_cache_manager is None:
        import os
        redis_host = os.getenv("REDIS_HOST", "localhost")
        redis_port = int(os.getenv("REDIS_PORT", "6379"))
        redis_db = int(os.getenv("REDIS_DB", "0"))
        redis_password = os.getenv("REDIS_PASSWORD")
        
        _global_cache_manager = CacheManager(
            redis_host=redis_host,
            redis_port=redis_port,
            redis_db=redis_db,
            redis_password=redis_password,
        )
    
    return _global_cache_manager

