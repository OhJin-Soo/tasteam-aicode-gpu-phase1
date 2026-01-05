FROM runpod/pytorch:1.0.2-cu1281-torch280-ubuntu2404

ENV PYTHONUNBUFFERED=1
WORKDIR /app

# 시스템 의존성
RUN apt-get update --yes && \
    DEBIAN_FRONTEND=noninteractive apt-get install --yes --no-install-recommends \
        wget curl git build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Flash Attention-2 설치 (Phase 1)
RUN (pip install flash-attn==2.5.6 --no-build-isolation || echo "Flash Attention-2 설치 실패")

# Hugging Face 설정 (런타임에 덮어쓸 수 있음)
ENV HF_HOME=/workspace/models
ENV HF_HUB_ENABLE_HF_TRANSFER=0

# 모델 다운로드는 런타임 스크립트로 처리 (환경변수 제어)
COPY . /app
COPY run.sh /app/run.sh
RUN chmod +x /app/run.sh

CMD ["/app/run.sh"]