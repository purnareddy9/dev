# ==========================================
# Production Multi-Stage Spring Boot Dockerfile
# Layered JAR Extraction for Maximum Cache Efficiency
# ==========================================
# Stage 1: Build Application with Maven
FROM maven:3.9.6-eclipse-temurin-21-jammy AS builder
WORKDIR /workspace

# Cache Maven dependencies layer
COPY pom.xml .
RUN mvn dependency:go-offline -B

# Compile and package application
COPY src ./src
RUN mvn clean package -DskipTests -B

# Stage 2: Extract Spring Boot Layers using layertools
WORKDIR /workspace/target
RUN java -Djarmode=layertools -jar *.jar extract

# Stage 3: Minimal Production JRE Runtime
FROM eclipse-temurin:21-jre-jammy AS runner
WORKDIR /application

# Non-root security user
RUN groupadd -r spring && useradd -r -g spring spring

# Copy extracted layers in order of frequency of change (Least frequent -> Most frequent)
COPY --from=builder --chown=spring:spring /workspace/target/dependencies/ ./
COPY --from=builder --chown=spring:spring /workspace/target/spring-boot-loader/ ./
COPY --from=builder --chown=spring:spring /workspace/target/snapshot-dependencies/ ./
COPY --from=builder --chown=spring:spring /workspace/target/application/ ./

USER spring
EXPOSE 8080

# Production JVM ergonomics for container cgroups
ENV JAVA_TOOL_OPTIONS="-XX:+UseContainerSupport -XX:MaxRAMPercentage=75.0 -XX:+UseG1GC"

ENTRYPOINT ["java", "org.springframework.boot.loader.launch.JarLauncher"]
