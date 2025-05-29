FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    git \
    build-essential \
    nodejs \
    npm \
    && rm -rf /var/lib/apt/lists/*


WORKDIR /app

# 코드 복사 (git clone 제거)
# 내부 패키지(opencv_mcp_server)만 복사
COPY opencv_mcp_server/opencv_mcp_server /app/opencv_mcp_server
COPY proxy-server.js /app/proxy-server.js

# RUN pip install git+https://github.com/fastmcp/mcp.git

# Python 의존성 설치
# RUN pip install .
RUN pip install opencv-python mcp 

# Node 설정
RUN npm init -y && npm pkg set type=module && npm install express body-parser

EXPOSE 8160

# 실행
CMD bash -c "PYTHONPATH=/app python3 -m opencv_mcp_server.main & sleep 2 && node /app/proxy-server.js"
