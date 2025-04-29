# 1. OpenJDK 17 기반의 가벼운 Alpine 이미지 사용
FROM openjdk:17-alpine

# 2. 작업 디렉토리 생성
WORKDIR /gateway

# 3. 빌드된 Spring Boot jar 파일 복사
COPY build/libs/*.jar app.jar

# 4. 필요한 경우 (시간대 설정 - 옵션)
RUN apk add --no-cache tzdata \
    && cp /usr/share/zoneinfo/Asia/Seoul /etc/localtime \
    && echo "Asia/Seoul" > /etc/timezone \
    && apk del tzdata

# 5. 실행
ENTRYPOINT ["java", "-jar", "/gateway/app.jar"]

# 6. (선택) 외부에 포트 오픈
EXPOSE 8090
