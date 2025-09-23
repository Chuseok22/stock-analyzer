# Multi-stage build for production optimization
FROM python:3.11-slim AS builder

# 빌드 인수 설정 (GitHub Actions에서 전달)
ARG GIT_SHA
ARG BUILD_TIME

# 메타데이터 추가
LABEL maintainer="chuseok22"
LABEL description="AI-powered Global Stock Trading Analysis System"
LABEL version="2.0"
LABEL git.sha="${GIT_SHA}"
LABEL build.time="${BUILD_TIME}"

# 환경 변수 설정
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PIP_NO_CACHE_DIR=1
ENV PIP_DISABLE_PIP_VERSION_CHECK=1

# 시스템 패키지 업데이트 및 빌드 도구 설치
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# 작업 디렉토리 설정
WORKDIR /tmp

# requirements.txt 복사 및 Python 의존성 설치
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# === Production Stage ===
FROM python:3.11-slim AS production

# 빌드 인수를 환경 변수로 전달
ARG GIT_SHA
ARG BUILD_TIME
ENV GIT_SHA=${GIT_SHA}
ENV BUILD_TIME=${BUILD_TIME}

# 런타임 환경 변수 설정
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONPATH=/app
ENV TZ=Asia/Seoul
ENV PORT=8080

# 런타임 패키지 설치
RUN apt-get update && apt-get install -y \
    curl \
    tzdata \
    && ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# 애플리케이션 사용자 생성 (보안 강화)
RUN groupadd -r appgroup && useradd -r -g appgroup -m appuser

# 작업 디렉토리 생성
WORKDIR /app

# Python 패키지 복사 (builder stage에서)
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# 애플리케이션 코드 복사
COPY app/ ./app/
COPY scripts/ ./scripts/
COPY database/ ./database/

# 실행 스크립트 복사
COPY tools/system/run_global_system.py ./run_global_system.py

# 실행 권한 부여
RUN find ./scripts -name "*.py" -exec chmod +x {} \; && \
    chmod +x run_global_system.py

# 필요한 디렉토리 생성
RUN mkdir -p /app/data \
             /app/logs \
             /app/storage/logs \
             /app/storage/models \
             /app/storage/reports \
             /app/storage/data \
             /app/storage/features \
             /app/storage/analysis_reports \
             /app/temp

# 디렉토리 소유권 변경
RUN chown -R appuser:appgroup /app

# 볼륨 마운트 포인트 설정 (외부 데이터 연동)
VOLUME ["/app/data", "/app/logs"]

# 사용자 전환 (보안 강화)
USER appuser

# 포트 노출 (GitHub Actions에서 설정한 포트와 일치)
EXPOSE 8080

# 헬스체크 설정 (GitHub Actions 배포 검증용)
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:${PORT}/health || exit 1

# 기본 실행 명령어 (인수 없이 실행 시 스케줄러 모드)
CMD ["python", "run_global_system.py"]