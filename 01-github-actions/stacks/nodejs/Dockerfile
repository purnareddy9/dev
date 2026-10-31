# ==========================================
# Production Multi-Stage Node.js Dockerfile
# ==========================================
# Stage 1: Build & Transpile TypeScript
FROM node:20-alpine AS builder
WORKDIR /app

# Copy dependency manifests first for maximum Docker layer caching
COPY package*.json tsconfig.json ./
RUN npm ci

# Copy source code and transpile to JavaScript
COPY src/ ./src/
RUN npm run build

# Remove development dependencies to keep production footprint minimal
RUN npm prune --production

# Stage 2: Hardened Production Runtime (Distroless)
FROM gcr.io/distroless/nodejs20-debian12:nonroot
WORKDIR /app

# Copy production node_modules and compiled JS output
COPY --from=builder --chown=nonroot:nonroot /app/node_modules ./node_modules
COPY --from=builder --chown=nonroot:nonroot /app/dist ./dist
COPY --from=builder --chown=nonroot:nonroot /app/package.json ./package.json

USER nonroot
EXPOSE 3000
ENV NODE_ENV=production

ENTRYPOINT ["node", "dist/index.js"]
