FROM eclipse-temurin:17-jdk AS build
WORKDIR /workspace
COPY gradlew* settings.gradle build.gradle gradle/ ./
RUN ./gradlew dependencies --no-daemon
COPY src ./src
RUN ./gradlew bootJar --no-daemon

FROM eclipse-temurin:17-jre
WORKDIR /app
COPY --from=build /workspace/build/libs/*.jar app.jar
EXPOSE 8000
HEALTHCHECK CMD curl -f http://localhost:8000/actuator/health || exit 1
ENTRYPOINT ["java","-jar","/app/app.jar"]
