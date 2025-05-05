#!/usr/bin/env bash
set -e

# 1) 이미지 빌드 (최초 1회, 이후 변경 시만)
docker build -t jenkins-docker:latest "$(dirname "$0")"

# 2) 볼륨이 없으면 생성
docker volume create --name jenkins_home >/dev/null 2>&1 || true

# 3) 컨테이너 실행
docker run -d --name jenkins \
  -p 8088:8080 -p 50000:50000 \
  -v jenkins_home:/var/jenkins_home \
  -v /var/run/docker.sock:/var/run/docker.sock \
  --restart unless-stopped \
  jenkins-docker:latest

