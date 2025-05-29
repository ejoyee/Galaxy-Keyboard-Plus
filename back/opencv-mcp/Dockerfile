FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    git \
    build-essential \
    nodejs \
    npm \
    # OpenCV를 위한 시스템 라이브러리들
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 전체 프로젝트 복사 (pyproject.toml 포함)
COPY opencv_mcp_server/ /app/
COPY proxy-server.js /app/proxy-server.js

# 개발용 설치 (editable install)
RUN pip install -e .

# Node 설정
RUN npm init -y && npm pkg set type=module && npm install express body-parser

EXPOSE 8160

CMD ["node", "/app/proxy-server.js"]