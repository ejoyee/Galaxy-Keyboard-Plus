# back/rag/Dockerfile

FROM python:3.11-slim
ENV GOOGLE_APPLICATION_CREDENTIALS=/app/gcp-key.json
# 파이썬 설정
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# 1) requirements.txt 복사 및 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 2) 앱 코드 복사
COPY app/ ./app


# 4) 실행 커맨드
CMD ["uvicorn","app.main:app","--host","0.0.0.0","--port","8090"]
