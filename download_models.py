"""
환경변수 기반 모델 다운로드 스크립트
"""
import os
import logging
from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline
from sentence_transformers import SentenceTransformer

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def download_models():
    """환경변수에 따라 모델 다운로드"""
    
    # 다운로드 여부 제어
    download_llm = os.getenv("PRE_DOWNLOAD_LLM", "true").lower() == "true"
    download_sentiment = os.getenv("PRE_DOWNLOAD_SENTIMENT", "true").lower() == "true"
    download_embedding = os.getenv("PRE_DOWNLOAD_EMBEDDING", "true").lower() == "true"
    
    # LLM 모델
    if download_llm:
        llm_model = os.getenv("LLM_MODEL", "Qwen/Qwen2.5-7B-Instruct")
        logger.info(f"LLM 모델 다운로드 시작: {llm_model}")
        try:
            tokenizer = AutoTokenizer.from_pretrained(llm_model, trust_remote_code=True)
            model = AutoModelForCausalLM.from_pretrained(llm_model, trust_remote_code=True)
            logger.info(f"✅ LLM 모델 다운로드 완료: {llm_model}")
        except Exception as e:
            logger.error(f"❌ LLM 모델 다운로드 실패: {e}")
    
    # 감성 분석 모델
    if download_sentiment:
        sentiment_model = os.getenv("SENTIMENT_MODEL", "Dilwolf/Kakao_app-kr_sentiment")
        logger.info(f"감성 분석 모델 다운로드 시작: {sentiment_model}")
        try:
            pipeline("sentiment-analysis", model=sentiment_model)
            logger.info(f"✅ 감성 분석 모델 다운로드 완료: {sentiment_model}")
        except Exception as e:
            logger.error(f"❌ 감성 분석 모델 다운로드 실패: {e}")
    
    # 임베딩 모델
    if download_embedding:
        embedding_model = os.getenv("EMBEDDING_MODEL", "jhgan/ko-sbert-multitask")
        logger.info(f"임베딩 모델 다운로드 시작: {embedding_model}")
        try:
            SentenceTransformer(embedding_model)
            logger.info(f"✅ 임베딩 모델 다운로드 완료: {embedding_model}")
        except Exception as e:
            logger.error(f"❌ 임베딩 모델 다운로드 실패: {e}")

if __name__ == "__main__":
    download_models()