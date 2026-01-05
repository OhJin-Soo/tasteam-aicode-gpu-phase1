#!/bin/bash
# 1. 포트 점유 중인 프로세스가 있다면 미리 죽이기 (강제 초기화)
fuser -k 8001/tcp || true

# 2. RunPod 기본 서비스 시작 (백그라운드)
/start.sh &

# 환경변수로 모델 다운로드 제어
if [ "${PRE_DOWNLOAD_MODELS:-false}" = "true" ]; then
    echo "=== 모델 사전 다운로드 시작 ==="
    python /app/download_models.py
    echo "=== 모델 다운로드 완료 ==="
fi

# 4. 앱 실행
# --reload 옵션은 Docker 환경에서 리소스 소모가 크므로 운영 시에는 빼는 것이 좋습니다.
python /app/app.py