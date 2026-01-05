"""
vLLM 서버 모듈 (Phase 2: LLM 서빙 최적화)

Qwen2.5-7B-Instruct 모델을 vLLM으로 서빙하여 성능을 향상시킵니다.
"""
import os
import logging
from typing import Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)

# vLLM 임포트 (선택적)
try:
    from vllm import LLM, SamplingParams
    VLLM_AVAILABLE = True
except ImportError:
    VLLM_AVAILABLE = False
    logger.warning("vLLM이 설치되지 않았습니다. vLLM 서버를 사용할 수 없습니다.")

app = FastAPI(title="vLLM Server", version="1.0.0")

# 전역 변수
llm_instance: Optional[LLM] = None
default_sampling_params: Optional[SamplingParams] = None


class GenerateRequest(BaseModel):
    """생성 요청 모델"""
    prompt: str
    temperature: float = 0.3
    max_tokens: int = 150
    top_p: float = 0.95


class GenerateResponse(BaseModel):
    """생성 응답 모델"""
    text: str
    finish_reason: str = "stop"


def initialize_vllm(
    model_name: str = "Qwen/Qwen2.5-7B-Instruct",
    tensor_parallel_size: int = 1,
    gpu_memory_utilization: float = 0.9,
    max_model_len: int = 4096,
    dtype: str = "float16",
):
    """
    vLLM 인스턴스를 초기화합니다.
    
    Args:
        model_name: 사용할 모델명
        tensor_parallel_size: 텐서 병렬 크기 (단일 GPU는 1)
        gpu_memory_utilization: GPU 메모리 활용률 (0.0 ~ 1.0)
        max_model_len: 최대 모델 길이
        dtype: 데이터 타입 (float16 또는 float32)
    """
    global llm_instance, default_sampling_params
    
    if not VLLM_AVAILABLE:
        raise ImportError("vLLM이 설치되지 않았습니다. pip install vllm로 설치하세요.")
    
    logger.info(f"vLLM 초기화 중: {model_name}")
    
    try:
        llm_instance = LLM(
            model=model_name,
            tensor_parallel_size=tensor_parallel_size,
            gpu_memory_utilization=gpu_memory_utilization,
            max_model_len=max_model_len,
            dtype=dtype,
            trust_remote_code=True,
        )
        
        default_sampling_params = SamplingParams(
            temperature=0.3,
            top_p=0.95,
            max_tokens=150,  # 짧은 응답에 최적화
        )
        
        logger.info("✅ vLLM 초기화 완료")
    except Exception as e:
        logger.error(f"vLLM 초기화 실패: {str(e)}")
        raise


@app.on_event("startup")
async def startup_event():
    """서버 시작 시 vLLM 초기화"""
    model_name = os.getenv("LLM_MODEL", "Qwen/Qwen2.5-7B-Instruct")
    tensor_parallel_size = int(os.getenv("TENSOR_PARALLEL_SIZE", "1"))
    gpu_memory_utilization = float(os.getenv("GPU_MEMORY_UTILIZATION", "0.9"))
    max_model_len = int(os.getenv("MAX_MODEL_LEN", "4096"))
    dtype = os.getenv("VLLM_DTYPE", "float16")
    
    if VLLM_AVAILABLE:
        try:
            initialize_vllm(
                model_name=model_name,
                tensor_parallel_size=tensor_parallel_size,
                gpu_memory_utilization=gpu_memory_utilization,
                max_model_len=max_model_len,
                dtype=dtype,
            )
        except Exception as e:
            logger.error(f"vLLM 초기화 실패: {str(e)}")
            logger.warning("vLLM 서버가 정상적으로 작동하지 않을 수 있습니다.")
    else:
        logger.warning("vLLM이 설치되지 않아 서버가 제한적으로 작동합니다.")


@app.get("/health")
async def health_check():
    """헬스 체크 엔드포인트"""
    if not VLLM_AVAILABLE:
        return {"status": "unavailable", "reason": "vLLM not installed"}
    if llm_instance is None:
        return {"status": "not_initialized"}
    return {"status": "healthy", "model": "Qwen/Qwen2.5-7B-Instruct"}


@app.post("/generate", response_model=GenerateResponse)
async def generate(request: GenerateRequest):
    """
    텍스트를 생성합니다.
    
    Args:
        request: 생성 요청
        
    Returns:
        생성된 텍스트
    """
    if not VLLM_AVAILABLE:
        raise HTTPException(status_code=503, detail="vLLM이 설치되지 않았습니다.")
    
    if llm_instance is None:
        raise HTTPException(status_code=503, detail="vLLM이 초기화되지 않았습니다.")
    
    try:
        # SamplingParams 생성
        sampling_params = SamplingParams(
            temperature=request.temperature,
            top_p=request.top_p,
            max_tokens=request.max_tokens,
        )
        
        # 생성 실행
        outputs = llm_instance.generate([request.prompt], sampling_params)
        
        if not outputs or len(outputs) == 0:
            raise HTTPException(status_code=500, detail="생성 결과가 없습니다.")
        
        output = outputs[0]
        if not output.outputs or len(output.outputs) == 0:
            raise HTTPException(status_code=500, detail="생성된 텍스트가 없습니다.")
        
        generated_text = output.outputs[0].text
        finish_reason = output.outputs[0].finish_reason or "stop"
        
        return GenerateResponse(text=generated_text, finish_reason=finish_reason)
        
    except Exception as e:
        logger.error(f"생성 중 오류 발생: {str(e)}")
        raise HTTPException(status_code=500, detail=f"생성 실패: {str(e)}")


@app.post("/generate_batch")
async def generate_batch(prompts: list[str], temperature: float = 0.3, max_tokens: int = 150):
    """
    여러 프롬프트를 배치로 생성합니다.
    
    Args:
        prompts: 프롬프트 리스트
        temperature: 생성 온도
        max_tokens: 최대 토큰 수
        
    Returns:
        생성된 텍스트 리스트
    """
    if not VLLM_AVAILABLE:
        raise HTTPException(status_code=503, detail="vLLM이 설치되지 않았습니다.")
    
    if llm_instance is None:
        raise HTTPException(status_code=503, detail="vLLM이 초기화되지 않았습니다.")
    
    try:
        sampling_params = SamplingParams(
            temperature=temperature,
            top_p=0.95,
            max_tokens=max_tokens,
        )
        
        outputs = llm_instance.generate(prompts, sampling_params)
        
        results = []
        for output in outputs:
            if output.outputs and len(output.outputs) > 0:
                results.append(output.outputs[0].text)
            else:
                results.append("")
        
        return {"texts": results}
        
    except Exception as e:
        logger.error(f"배치 생성 중 오류 발생: {str(e)}")
        raise HTTPException(status_code=500, detail=f"배치 생성 실패: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    
    port = int(os.getenv("VLLM_PORT", "8001"))
    host = os.getenv("VLLM_HOST", "0.0.0.0")
    
    uvicorn.run(app, host=host, port=port)

