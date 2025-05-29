FROM node:18-slim

WORKDIR /app

# 초기화 및 의존성 설치
RUN npm init -y && \
    npm install express body-parser && \
    npm install -g @openbnb/mcp-server-airbnb

# 프록시 서버 파일 복사
COPY proxy-server.js .

# ES Module 설정
RUN node -e "const pkg=require('./package.json'); pkg.type='module'; require('fs').writeFileSync('./package.json', JSON.stringify(pkg, null, 2))"

EXPOSE 8180

HEALTHCHECK --interval=30s --timeout=3s \
  CMD curl -f http://localhost:8180/health || exit 1

CMD ["node", "proxy-server.js"]
