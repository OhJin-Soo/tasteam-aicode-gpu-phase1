#!/bin/bash
# Start base image services (Jupyter/SSH) in background
/start.sh &

# Wait for services to start
sleep 2

# 환경변수로 모델 다운로드 제어
if [ "${PRE_DOWNLOAD_MODELS:-false}" = "true" ]; then
    echo "=== 모델 사전 다운로드 시작 ==="
    python /app/download_models.py
    echo "=== 모델 다운로드 완료 ==="
fi

# Run your application
python /app/app.py

# Wait for background processes
wait