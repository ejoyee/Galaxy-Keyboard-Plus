# =============== 1) Build Stage ===============================
FROM eclipse-temurin:17-jdk AS build
WORKDIR /workspace

# gradlew 및 빌드 설정 복사
COPY gradlew* settings.gradle build.gradle gradle/ ./

# ★ gradlew 실행권한 부여 ────────────────
RUN chmod +x gradlew

# 의존성 사전 다운로드
RUN ./gradlew dependencies --no-daemon

# 애플리케이션 소스 복사 후 JAR 빌드
COPY src ./src
RUN ./gradlew bootJar --no-daemon


# =============== 2) Runtime Stage =============================
FROM eclipse-temurin:17-jre
WORKDIR /app

# 빌드된 JAR만 복사
COPY --from=build /workspace/build/libs/*.jar app.jar

EXPOSE 8000
HEALTHCHECK CMD curl -f http://localhost:8000/actuator/health || exit 1

ENTRYPOINT ["java", "-jar", "/app/app.jar"]
