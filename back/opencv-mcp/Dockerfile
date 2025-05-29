FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    git build-essential nodejs npm \
    libglib2.0-0 libsm6 libxext6 libxrender-dev libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY opencv_mcp_server/ /app/
COPY proxy-server.js /app/proxy-server.js

RUN pip install -e . && \
    npm init -y && npm pkg set type=module && npm install express body-parser

# 환경 변수 추가
ENV PYTHONUNBUFFERED=1
ENV PYTHONIOENCODING=utf-8

EXPOSE 8160
CMD ["node", "/app/proxy-server.js"]