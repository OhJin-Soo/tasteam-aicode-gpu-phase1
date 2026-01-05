"""
LLM 유틸리티 모듈 (Qwen2.5-7B-Instruct 사용)
"""

import json
import logging
import os
import re
import torch
from typing import Dict, List, Optional, Any

from transformers import AutoModelForCausalLM, AutoTokenizer

from .config import Config

logger = logging.getLogger(__name__)


class LLMUtils:
    """LLM 관련 유틸리티 클래스 (Qwen 모델 사용)"""
    
    def __init__(
        self,
        model_name: str = Config.LLM_MODEL,
        device: Optional[str] = None,
    ):
        """
        Args:
            model_name: 사용할 모델명 (기본값: Qwen/Qwen2.5-7B-Instruct)
            device: 사용할 디바이스 (None이면 자동 선택: cuda > mps > cpu)
        """
        self.model_name = model_name
        
        # 디바이스 자동 선택
        if device is None:
            if torch.cuda.is_available():
                device = "cuda"
            elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
                device = "mps"
            else:
                device = "cpu"
        self.device = device
        
        logger.info(f"Qwen 모델 로딩 중: {model_name} (device: {device})")
        
        # 모델과 토크나이저 로드
        self.tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
        
        # Flash Attention-2 적용 시도 (설치되어 있으면 사용)
        attn_implementation = None
        try:
            import flash_attn
            attn_implementation = "flash_attention_2"
            logger.info("Flash Attention-2 사용 가능, 적용합니다.")
        except ImportError:
            logger.info("Flash Attention-2가 설치되지 않았습니다. 기본 attention을 사용합니다.")
        
        model_kwargs = {
            "torch_dtype": torch.float16 if device != "cpu" else torch.float32,
            "device_map": "auto" if device != "cpu" else None,
            "trust_remote_code": True,
        }
        
        if attn_implementation:
            model_kwargs["attn_implementation"] = attn_implementation
        
        self.model = AutoModelForCausalLM.from_pretrained(
            model_name,
            **model_kwargs
        )
        
        # 배치 크기 동적 조정
        self.batch_size = Config.get_optimal_batch_size("llm")
        
        if device == "cpu":
            self.model = self.model.to(device)
        
        self.model.eval()
        logger.info(f"✅ Qwen 모델 로딩 완료: {model_name}")
    
    def _fix_truncated_json(self, text: str) -> str:
        """
        잘린 JSON 문자열을 복구합니다.
        
        Args:
            text: 잘린 JSON 문자열
            
        Returns:
            복구된 JSON 문자열
        """
        # 마지막 불완전한 문자열 필드를 닫기
        text = text.strip()
        
        # 마지막 따옴표가 닫히지 않은 경우
        if text.count('"') % 2 != 0:
            # 마지막 따옴표 뒤에 닫는 따옴표 추가
            last_quote_idx = text.rfind('"')
            if last_quote_idx != -1:
                # 마지막 따옴표 뒤에 닫는 따옴표와 중괄호 추가
                text = text[:last_quote_idx + 1] + '"'
        
        # 중괄호가 닫히지 않은 경우
        open_braces = text.count('{')
        close_braces = text.count('}')
        if open_braces > close_braces:
            # 닫는 중괄호 추가
            text += '}' * (open_braces - close_braces)
        
        return text
    
    def _generate_response(
        self, 
        messages: List[Dict[str, str]], 
        temperature: float = 0.3,
        max_new_tokens: int = 50,
    ) -> str:
        """
        Qwen 모델을 사용하여 응답을 생성합니다.
        
        Args:
            messages: 대화 메시지 리스트 (OpenAI 형식)
            temperature: 생성 온도
            max_new_tokens: 최대 생성 토큰 수 (기본값: 50, 요약/강점 추출 시 더 큰 값 필요)
            
        Returns:
            생성된 응답 텍스트
        """
        # Transformers 방식
        # Qwen chat template 형식으로 변환
        text = self.tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True
        )
        
        # 토크나이징
        model_inputs = self.tokenizer([text], return_tensors="pt").to(self.device)
        
        # 생성 (최적화 옵션 적용)
        with torch.no_grad():
            generate_kwargs = {
                **model_inputs,
                "max_new_tokens": max_new_tokens,
                "num_beams": 1,  # beam search 비활성화 (빠름)
                "use_cache": True,  # KV 캐시 사용 (빠름)
                "pad_token_id": self.tokenizer.eos_token_id,
            }
            
            # do_sample=True일 때만 샘플링 파라미터 추가 (경고 메시지 방지)
            if temperature > 0.1:
                generate_kwargs["temperature"] = temperature
                generate_kwargs["do_sample"] = True
            else:
                generate_kwargs["do_sample"] = False
            
            generated_ids = self.model.generate(**generate_kwargs)
        
        # 디코딩
        generated_ids = [
            output_ids[len(input_ids):] for input_ids, output_ids in zip(model_inputs.input_ids, generated_ids)
        ]
        response = self.tokenizer.batch_decode(generated_ids, skip_special_tokens=True)[0]
        response = response.strip()
        
        return response
    
    def classify_reviews(
        self,
        texts: List[str],
        max_retries: int = Config.MAX_RETRIES,
        batch_size: Optional[int] = None,
    ) -> List[Dict]:
        """
        LLM을 사용하여 텍스트들을 분류합니다. (배치 처리)
        
        Args:
            texts: 분류할 텍스트 리스트
            max_retries: 최대 재시도 횟수
            batch_size: 배치 크기 (None이면 자동으로 최적 크기 사용)
            
        Returns:
            분류 결과 리스트
        """
        if not texts:
            return []
        
        if batch_size is None:
            batch_size = self.batch_size
        
        all_results = []
        total_batches = (len(texts) + batch_size - 1) // batch_size
        
        logger.info(f"총 {len(texts)}개 리뷰를 {total_batches}개 배치로 분류합니다 (배치 크기: {batch_size})")
        
        # 배치별로 처리
        for batch_idx in range(0, len(texts), batch_size):
            batch = texts[batch_idx:batch_idx + batch_size]
            current_batch_num = batch_idx // batch_size + 1
            
            logger.debug(f"배치 {current_batch_num}/{total_batches} 처리 중 ({len(batch)}개 리뷰)")
            
            # 각 배치에 대해 재시도 로직 적용
            batch_results = None
            for attempt in range(max_retries):
                try:
                    messages = [
                        {
                            "role": "system",
                            "content": (
                                "너는 긍정/부정 분류를 잘하는 AI 어시스턴트다.\n"
                                "다음 문장들에 대해 positive/negative를 판단하여라.\n"
                                "하나의 문장에 긍/부정이 섞였다면, 전체적인 톤에 따라 하나의 라벨을 선택하라.\n"
                                "반드시 **JSON 표준**(큰따옴표)으로 배열 형태 출력\n"
                                "예시: [{\"label\":\"positive\",\"text\":\"...\"}, {\"label\":\"negative\",\"text\":\"...\"}]\n"
                                "작은따옴표(') 사용 금지"
                            ),
                        },
                        {
                            "role": "user",
                            "content": json.dumps({"reviews": batch}, ensure_ascii=False),
                        },
                    ]
                    
                    response_text = self._generate_response(messages, temperature=0.1)
                    logger.debug(f"배치 {current_batch_num} LLM 응답: {response_text[:200]}...")
                    
                    # JSON 파싱 시도
                    try:
                        llm_results = json.loads(response_text)
                        if isinstance(llm_results, list):
                            # 결과 개수 확인
                            if len(llm_results) == len(batch):
                                batch_results = llm_results
                                break  # 성공 시 재시도 루프 탈출
                            else:
                                logger.warning(
                                    f"배치 {current_batch_num}: 결과 개수 불일치 "
                                    f"(예상: {len(batch)}, 실제: {len(llm_results)}). 재시도합니다."
                                )
                        else:
                            logger.warning(f"배치 {current_batch_num}: LLM 응답이 리스트가 아닙니다. 재시도합니다.")
                    except json.JSONDecodeError as e:
                        logger.warning(
                            f"배치 {current_batch_num}: JSON 파싱 실패 "
                            f"(시도 {attempt + 1}/{max_retries}): {str(e)}"
                        )
                        logger.debug(f"원문: {response_text[:500]}")
                        
                        # 마지막 시도가 아니면 재시도
                        if attempt < max_retries - 1:
                            continue
                        else:
                            logger.error(f"배치 {current_batch_num}: 모든 재시도 실패. 빈 결과 반환.")
                            batch_results = []
                            break
                            
                except Exception as e:
                    logger.error(
                        f"배치 {current_batch_num}: LLM 호출 중 오류 발생 "
                        f"(시도 {attempt + 1}/{max_retries}): {str(e)}"
                    )
                    if attempt < max_retries - 1:
                        continue
                    else:
                        logger.error(f"배치 {current_batch_num}: 모든 재시도 실패.")
                        batch_results = []
                        break
            
            # 배치 결과 추가
            if batch_results is None:
                logger.warning(f"배치 {current_batch_num}: 결과를 얻지 못했습니다. 빈 결과 반환.")
                batch_results = []
            
            all_results.extend(batch_results)
            logger.debug(f"배치 {current_batch_num} 완료: {len(batch_results)}개 결과")
        
        logger.info(f"✅ 전체 분류 완료: {len(all_results)}개 결과 반환")
        return all_results
    
    def count_sentiments(
        self,
        texts: List[str],
        max_retries: int = Config.MAX_RETRIES,
        batch_size: Optional[int] = None,
    ) -> Dict[str, int]:
        """
        LLM을 사용하여 리뷰들의 긍정/부정 개수를 집계합니다. (배치 처리, 동적 크기 조정)
        
        리뷰를 배치로 나눠서 처리하고, 각 배치의 개수를 집계하여 최종 결과를 반환합니다.
        리뷰 수에 따라 배치 크기를 동적으로 조정하여 성능을 최적화합니다.
        
        Args:
            texts: 분류할 텍스트 리스트
            max_retries: 최대 재시도 횟수
            batch_size: 배치 크기 (None이면 자동으로 최적 크기 사용)
            
        Returns:
            {"positive_count": int, "negative_count": int}
        """
        if not texts:
            return {"positive_count": 0, "negative_count": 0}
        
        if batch_size is None:
            batch_size = self.batch_size
        
        # 동적 배치 크기 조정
        num_reviews = len(texts)
        if num_reviews > 50:
            # 대량 리뷰: 배치 크기 증가 (최대 20개)
            adjusted_batch_size = min(batch_size * 2, 20)
            logger.info(f"대량 리뷰 감지 ({num_reviews}개): 배치 크기 {batch_size} → {adjusted_batch_size}로 증가")
        elif num_reviews > 20:
            # 중간 리뷰: 배치 크기 약간 증가
            adjusted_batch_size = min(int(batch_size * 1.5), 15)
            logger.info(f"중간 리뷰 감지 ({num_reviews}개): 배치 크기 {batch_size} → {adjusted_batch_size}로 증가")
        elif num_reviews <= 10:
            # 소량 리뷰: 한 번에 처리
            adjusted_batch_size = num_reviews
            logger.info(f"소량 리뷰 감지 ({num_reviews}개): 배치 크기 {batch_size} → {adjusted_batch_size}로 조정 (한 번에 처리)")
        else:
            # 기본 배치 크기 유지
            adjusted_batch_size = batch_size
        
        total_positive = 0
        total_negative = 0
        total_batches = (num_reviews + adjusted_batch_size - 1) // adjusted_batch_size
        
        logger.info(f"총 {num_reviews}개 리뷰를 {total_batches}개 배치로 나눠서 개수를 집계합니다 (배치 크기: {adjusted_batch_size})")
        
        # 배치별로 처리
        for batch_idx in range(0, num_reviews, adjusted_batch_size):
            batch = texts[batch_idx:batch_idx + adjusted_batch_size]
            current_batch_num = batch_idx // adjusted_batch_size + 1
            
            logger.debug(f"배치 {current_batch_num}/{total_batches} 처리 중 ({len(batch)}개 리뷰)")
            
            # 각 배치에 대해 재시도 로직 적용
            batch_counts = None
            for attempt in range(max_retries):
                try:
                    messages = [
                        {
                            "role": "system",
                            "content": (
                                "리뷰들을 읽고 긍정/부정 개수만 집계.\\n"
                                "JSON 형식: {\"positive_count\": 숫자, \"negative_count\": 숫자}"
                            ),
                        },
                        {
                            "role": "user",
                            "content": json.dumps({"reviews": batch}, ensure_ascii=False),
                        },
                    ]
                    
                    response_text = self._generate_response(messages, temperature=0.1)
                    logger.debug(f"배치 {current_batch_num} LLM 응답: {response_text[:200]}...")
                    
                    # JSON 파싱
                    try:
                        result = json.loads(response_text)
                        if isinstance(result, dict) and "positive_count" in result and "negative_count" in result:
                            positive_count = int(result["positive_count"])
                            negative_count = int(result["negative_count"])
                            
                            # 검증: 개수 합이 배치 리뷰 수와 일치하는지 확인
                            total_count = positive_count + negative_count
                            if total_count == len(batch):
                                # 정확히 일치: 그대로 사용
                                batch_counts = {"positive_count": positive_count, "negative_count": negative_count}
                                logger.debug(f"배치 {current_batch_num}: 긍정 {positive_count}개, 부정 {negative_count}개")
                                break  # 성공 시 재시도 루프 탈출
                            elif total_count > 0:
                                # 개수 불일치: 비율로 추정하여 즉시 반환 (재시도 없음)
                                logger.warning(
                                    f"배치 {current_batch_num}: 개수 불일치 "
                                    f"(예상: {len(batch)}, 실제: {total_count}). 비율로 추정하여 사용."
                                )
                                # 비율 계산하여 배치 크기에 맞게 조정
                                ratio = len(batch) / total_count
                                adjusted_positive = int(round(positive_count * ratio))
                                adjusted_negative = len(batch) - adjusted_positive
                                batch_counts = {
                                    "positive_count": adjusted_positive,
                                    "negative_count": adjusted_negative
                                }
                                logger.debug(
                                    f"배치 {current_batch_num}: 추정값 - 긍정 {adjusted_positive}개, "
                                    f"부정 {adjusted_negative}개"
                                )
                                break  # 즉시 반환 (재시도 없음)
                            else:
                                # total_count가 0인 경우에만 재시도
                                logger.warning(
                                    f"배치 {current_batch_num}: 개수 합이 0입니다. 재시도합니다."
                                )
                        else:
                            logger.warning(f"배치 {current_batch_num}: LLM 응답 형식이 올바르지 않습니다. 재시도합니다.")
                    except json.JSONDecodeError as e:
                        logger.warning(
                            f"배치 {current_batch_num}: JSON 파싱 실패 "
                            f"(시도 {attempt + 1}/{max_retries}): {str(e)}"
                        )
                        logger.debug(f"원문: {response_text[:500]}")
                        
                        if attempt < max_retries - 1:
                            continue
                        else:
                            logger.error(f"배치 {current_batch_num}: 모든 재시도 실패. 빈 결과 반환.")
                            batch_counts = {"positive_count": 0, "negative_count": 0}
                            break
                            
                except Exception as e:
                    logger.error(
                        f"배치 {current_batch_num}: LLM 호출 중 오류 발생 "
                        f"(시도 {attempt + 1}/{max_retries}): {str(e)}"
                    )
                    if attempt < max_retries - 1:
                        continue
                    else:
                        logger.error(f"배치 {current_batch_num}: 모든 재시도 실패.")
                        batch_counts = {"positive_count": 0, "negative_count": 0}
                        break
            
            # 배치 결과 집계
            if batch_counts is None:
                logger.warning(f"배치 {current_batch_num}: 결과를 얻지 못했습니다. 빈 결과로 처리.")
                batch_counts = {"positive_count": 0, "negative_count": 0}
            
            total_positive += batch_counts["positive_count"]
            total_negative += batch_counts["negative_count"]
            logger.debug(f"배치 {current_batch_num} 완료: 현재 누적 - 긍정 {total_positive}개, 부정 {total_negative}개")
        
        logger.info(f"✅ 전체 분류 완료: 긍정 {total_positive}개, 부정 {total_negative}개")
        return {"positive_count": total_positive, "negative_count": total_negative}
    
    def summarize_reviews(
        self,
        positive_reviews: List[Dict[str, Any]],
        negative_reviews: List[Dict[str, Any]],
    ) -> Dict:
        """
        긍정/부정 리뷰를 요약합니다. (메타데이터 포함)
        
        Args:
            positive_reviews: 긍정 리뷰 딕셔너리 리스트 (payload 포함)
            negative_reviews: 부정 리뷰 딕셔너리 리스트 (payload 포함)
            
        Returns:
            요약 결과 딕셔너리 (메타데이터 포함)
        """
        try:
            # 리뷰 텍스트만 추출
            positive_texts = [r.get("review", "") if isinstance(r, dict) else r for r in positive_reviews]
            negative_texts = [r.get("review", "") if isinstance(r, dict) else r for r in negative_reviews]
            
            # 빈 리뷰 제거
            positive_texts = [t for t in positive_texts if t]
            negative_texts = [t for t in negative_texts if t]
            
            if not positive_texts and not negative_texts:
                logger.warning("요약할 리뷰가 없습니다.")
                return {
                    "positive_summary": "",
                    "negative_summary": "",
                    "overall_summary": "요약할 리뷰가 없습니다."
                }
            
            messages = [
                {
                    "role": "system",
                    "content": (
                        "음식점 리뷰 요약 AI. **한국어로만 출력.**\n"
                        "긍정/부정 리뷰를 각각 요약하고 전체 요약 생성.\n"
                        "중복 제거, 핵심만 간결하게.\n"
                        "JSON: {\"positive_summary\": \"...\", \"negative_summary\": \"...\", \"overall_summary\": \"...\"}"
                    )
                },
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "positive_reviews": positive_texts,
                            "negative_reviews": negative_texts
                        },
                        ensure_ascii=False
                    )
                },
            ]
            
            # 요약은 더 긴 응답이 필요하므로 max_new_tokens 증가 (150으로 최적화, temperature 낮춤)
            response_text = self._generate_response(messages, temperature=0.1, max_new_tokens=150)
            
            # 응답이 비어있는지 확인
            if not response_text or not response_text.strip():
                logger.error("LLM이 빈 응답을 반환했습니다.")
                raise ValueError("LLM이 빈 응답을 반환했습니다.")
            
            # 마크다운 코드 블록 제거
            response_text = response_text.strip()
            if response_text.startswith("```json"):
                response_text = response_text[7:].strip()
            elif response_text.startswith("```"):
                response_text = response_text[3:].strip()
            if response_text.endswith("```"):
                response_text = response_text[:-3].strip()
            response_text = response_text.strip()
            
            # JSON 부분만 추출 (정규식 사용)
            json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', response_text, re.DOTALL)
            if json_match:
                response_text = json_match.group(0)
            
            # JSON 파싱 (잘린 JSON 복구 시도)
            try:
                summary = json.loads(response_text)
            except json.JSONDecodeError as e:
                logger.warning(f"JSON 파싱 실패, 복구 시도 중... (오류: {str(e)})")
                logger.debug(f"응답 텍스트 (처음 200자): {response_text[:200]}")
                # 잘린 JSON 복구 시도: 마지막 불완전한 문자열 필드 닫기
                response_text = self._fix_truncated_json(response_text)
                summary = json.loads(response_text)
            
            # 필수 키 확인
            required_keys = ["positive_summary", "negative_summary", "overall_summary"]
            for key in required_keys:
                if key not in summary:
                    logger.warning(f"응답에 {key} 키가 없습니다. 기본값 설정.")
                    summary[key] = ""
            
            # 메타데이터 추가
            summary["positive_reviews"] = positive_reviews
            summary["negative_reviews"] = negative_reviews
            summary["positive_count"] = len(positive_reviews)
            summary["negative_count"] = len(negative_reviews)
            
            return summary
        except json.JSONDecodeError as e:
            logger.error(f"JSON 파싱 실패: {str(e)}")
            if 'response_text' in locals():
                logger.error(f"응답: {response_text}")
            else:
                logger.error("응답 텍스트를 가져오지 못했습니다.")
            return {
                "positive_summary": "",
                "negative_summary": "",
                "overall_summary": "요약 실패",
                "positive_reviews": positive_reviews,
                "negative_reviews": negative_reviews,
                "positive_count": len(positive_reviews),
                "negative_count": len(negative_reviews),
            }
        except Exception as e:
            logger.error(f"리뷰 요약 중 오류: {str(e)}")
            return {
                "positive_summary": "",
                "negative_summary": "",
                "overall_summary": "요약 실패",
                "positive_reviews": positive_reviews,
                "negative_reviews": negative_reviews,
                "positive_count": len(positive_reviews),
                "negative_count": len(negative_reviews),
            }
    
    def extract_strengths(
        self,
        target_reviews: List[Dict[str, Any]],
        comparison_reviews: List[Dict[str, Any]],
        target_restaurant_id: str,
    ) -> Dict:
        """
        타겟 레스토랑의 강점을 추출합니다. (메타데이터 포함)
        
        Args:
            target_reviews: 타겟 레스토랑의 긍정 리뷰 딕셔너리 리스트 (payload 포함)
            comparison_reviews: 비교 대상 레스토랑의 긍정 리뷰 딕셔너리 리스트 (payload 포함)
            target_restaurant_id: 타겟 레스토랑 ID
            
        Returns:
            강점 요약 딕셔너리 (메타데이터 포함)
        """
        try:
            # 리뷰 텍스트만 추출
            target_texts = [r.get("review", "") if isinstance(r, dict) else r for r in target_reviews]
            comparison_texts = [r.get("review", "") if isinstance(r, dict) else r for r in comparison_reviews]
            
            # 빈 리뷰 제거
            target_texts = [t for t in target_texts if t]
            comparison_texts = [t for t in comparison_texts if t]
            
            if not target_texts:
                logger.warning("타겟 레스토랑의 리뷰가 없습니다.")
                return {
                    "strength_summary": "타겟 레스토랑의 리뷰가 없어 강점을 추출할 수 없습니다.",
                    "target_reviews": target_reviews,
                    "comparison_reviews": comparison_reviews,
                    "target_count": 0,
                    "comparison_count": len(comparison_reviews),
                }
            
            messages = [
                {
                    "role": "system",
                    "content": (
                        "음식점 리뷰 강점 추출 AI. **한국어로만 출력.**\n"
                        "타겟 레스토랑이 비교 대상 대비 어떤 점이 좋은지 추출.\n"
                        "중복 제거, 핵심만 간결하게. 강점 없으면 이유와 함께 제시.\n"
                        "JSON: {\"strength_summary\": \"...\"}"
                    )
                },
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "target_positive_reviews": target_texts,
                            "comparison_positive_reviews": comparison_texts
                        },
                        ensure_ascii=False
                    )
                }
            ]
            
            # 재시도 로직 (최대 2번 재시도)
            max_retries = 2
            result = None
            
            for attempt in range(max_retries + 1):
                try:
                    # 강점 추출은 더 긴 응답이 필요하므로 max_new_tokens 증가 (150으로 최적화, temperature 낮춤)
                    response_text = self._generate_response(messages, temperature=0.1, max_new_tokens=150)
                    
                    # 응답이 비어있는지 확인
                    if not response_text or not response_text.strip():
                        logger.warning(f"시도 {attempt + 1}: LLM이 빈 응답을 반환했습니다.")
                        if attempt < max_retries:
                            continue
                        else:
                            raise ValueError("LLM이 빈 응답을 반환했습니다.")
                    
                    # 마크다운 코드 블록 제거
                    response_text = response_text.strip()
                    if response_text.startswith("```json"):
                        response_text = response_text[7:].strip()
                    elif response_text.startswith("```"):
                        response_text = response_text[3:].strip()
                    if response_text.endswith("```"):
                        response_text = response_text[:-3].strip()
                    response_text = response_text.strip()
                    
                    # JSON 부분만 추출 (정규식 사용)
                    json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', response_text, re.DOTALL)
                    if json_match:
                        response_text = json_match.group(0)
                    
                    # JSON 파싱 (잘린 JSON 복구 시도)
                    try:
                        result = json.loads(response_text)
                    except json.JSONDecodeError as e:
                        logger.warning(f"시도 {attempt + 1}: JSON 파싱 실패, 복구 시도 중... (오류: {str(e)})")
                        # 잘린 JSON 복구 시도
                        response_text = self._fix_truncated_json(response_text)
                        result = json.loads(response_text)
                    
                    # strength_summary 키 확인
                    if not isinstance(result, dict):
                        raise ValueError(f"응답이 딕셔너리가 아닙니다. 타입: {type(result)}")
                    
                    if "strength_summary" not in result:
                        logger.warning(f"시도 {attempt + 1}: 응답에 strength_summary 키가 없습니다. 응답: {response_text[:200]}")
                        # 다른 키 이름 시도
                        result = {
                            "strength_summary": result.get(
                                "summary", 
                                result.get("strength", "분석 결과를 추출할 수 없습니다.")
                            )
                        }
                    
                    # 성공 시 루프 탈출
                    break
                    
                except (json.JSONDecodeError, ValueError, KeyError) as e:
                    if attempt < max_retries:
                        logger.warning(f"시도 {attempt + 1} 실패, 재시도 중... (오류: {str(e)})")
                        if 'response_text' in locals():
                            logger.debug(f"응답 텍스트 (처음 200자): {response_text[:200]}")
                        continue
                    else:
                        logger.error(f"모든 재시도 실패: {str(e)}")
                        if 'response_text' in locals():
                            logger.error(f"응답 텍스트 (처음 500자): {response_text[:500]}")
                            logger.error(f"응답 텍스트 (전체 길이): {len(response_text)}")
                        raise
            
            if result is None:
                raise ValueError("모든 재시도 실패: 결과를 얻을 수 없습니다.")
            
            # 메타데이터 추가
            result["target_restaurant_id"] = target_restaurant_id
            result["target_reviews"] = target_reviews
            result["comparison_reviews"] = comparison_reviews
            result["target_count"] = len(target_reviews)
            result["comparison_count"] = len(comparison_reviews)
            
            return result
        except json.JSONDecodeError as e:
            logger.error(f"JSON 파싱 실패: {str(e)}")
            return {
                "strength_summary": "분석 실패",
                "target_restaurant_id": target_restaurant_id,
                "target_reviews": target_reviews,
                "comparison_reviews": comparison_reviews,
                "target_count": len(target_reviews),
                "comparison_count": len(comparison_reviews),
            }
        except Exception as e:
            logger.error(f"강점 추출 중 오류: {str(e)}")
            return {
                "strength_summary": "분석 실패",
                "target_restaurant_id": target_restaurant_id,
                "target_reviews": target_reviews,
                "comparison_reviews": comparison_reviews,
                "target_count": len(target_reviews),
                "comparison_count": len(comparison_reviews),
            }


def summarize_reviews(
    llm_utils: LLMUtils,
    positive_reviews: List[Dict[str, Any]],
    negative_reviews: List[Dict[str, Any]],
) -> Dict:
    """
    긍정/부정 리뷰를 요약하는 편의 함수. (메타데이터 포함)
    
    Args:
        llm_utils: LLMUtils 인스턴스
        positive_reviews: 긍정 리뷰 딕셔너리 리스트 (payload 포함)
        negative_reviews: 부정 리뷰 딕셔너리 리스트 (payload 포함)
        
    Returns:
        요약 결과 딕셔너리 (메타데이터 포함)
    """
    return llm_utils.summarize_reviews(positive_reviews, negative_reviews)


def extract_strengths(
    llm_utils: LLMUtils,
    target_reviews: List[Dict[str, Any]],
    comparison_reviews: List[Dict[str, Any]],
    target_restaurant_id: str,
) -> Dict:
    """
    타겟 레스토랑의 강점을 추출하는 편의 함수. (메타데이터 포함)
    
    Args:
        llm_utils: LLMUtils 인스턴스
        target_reviews: 타겟 레스토랑의 긍정 리뷰 딕셔너리 리스트 (payload 포함)
        comparison_reviews: 비교 대상 레스토랑의 긍정 리뷰 딕셔너리 리스트 (payload 포함)
        target_restaurant_id: 타겟 레스토랑 ID
        
    Returns:
        강점 요약 딕셔너리 (메타데이터 포함)
    """
    return llm_utils.extract_strengths(target_reviews, comparison_reviews, target_restaurant_id)
