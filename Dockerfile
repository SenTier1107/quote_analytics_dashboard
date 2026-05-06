FROM python:3.11-slim

WORKDIR /app

# 시스템 패키지 설치 (한국어 폰트 포함)
RUN apt-get update && apt-get install -y \
    fonts-nanum \
    && rm -rf /var/lib/apt/lists/*

# 의존성 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 소스 코드 복사
COPY . .

# 시드 스크립트 실행 — PYTHONPATH 설정으로 core 모듈 인식
RUN PYTHONPATH=/app python scripts/seed.py
RUN PYTHONPATH=/app python scripts/seed_authors.py
RUN PYTHONPATH=/app python scripts/build_embeddings.py

# 포트 설정
EXPOSE 7860

# 서버 실행
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "7860"]