FROM node:18-slim

WORKDIR /app

RUN npm init -y \
 && npm install express body-parser \
 && npm install -g @modelcontextprotocol/server-google-maps

COPY proxy-server.js .

RUN node -e "const p=require('./package.json');p.type='module';require('fs').writeFileSync('./package.json',JSON.stringify(p,null,2));"

# ▶ 포트 변경
EXPOSE 8160

HEALTHCHECK --interval=30s --timeout=3s \
  CMD curl -f http://localhost:8160/health || exit 1

CMD ["node", "proxy-server.js"]
