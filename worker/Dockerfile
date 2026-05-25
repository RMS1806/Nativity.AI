# Multi-stage Dockerfile for Nativity.AI Worker Service
# Optimized for video processing workloads on AWS ECS Fargate

# Stage 1: Build stage
FROM node:18-alpine AS builder

# Set working directory
WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies (including dev dependencies for build)
RUN npm ci --only=production && npm cache clean --force

# Copy source code
COPY . .

# Build the application (if using TypeScript or build process)
# RUN npm run build

# Stage 2: Production stage with additional tools for video processing
FROM node:18-alpine AS production

# Install system dependencies for video processing
RUN apk update && apk upgrade && \
    apk add --no-cache \
    dumb-init \
    ffmpeg \
    python3 \
    py3-pip \
    curl \
    wget

# Install Python dependencies for AI processing
RUN pip3 install --no-cache-dir \
    google-generativeai \
    openai \
    boto3 \
    requests

# Create non-root user for security
RUN addgroup -g 1001 -S nodejs && \
    adduser -S nativity -u 1001

# Set working directory
WORKDIR /app

# Copy package files
COPY package*.json ./

# Install only production dependencies
RUN npm ci --only=production && npm cache clean --force

# Copy built application from builder stage
COPY --from=builder --chown=nativity:nodejs /app .

# Remove unnecessary files
RUN rm -rf src/ tests/ *.md Dockerfile .git* .env*

# Create necessary directories for processing
RUN mkdir -p logs tmp processing uploads downloads && \
    chown -R nativity:nodejs logs tmp processing uploads downloads

# Set up processing directory permissions
RUN chmod 755 processing uploads downloads

# Switch to non-root user
USER nativity

# Health check for worker service
HEALTHCHECK --interval=60s --timeout=10s --start-period=30s --retries=3 \
    CMD node healthcheck.js || exit 1

# Use dumb-init to handle signals properly
ENTRYPOINT ["dumb-init", "--"]

# Start the worker service
CMD ["node", "worker.js"]

# Labels for better container management
LABEL maintainer="Nativity.AI Team" \
      version="1.0.0" \
      description="Nativity.AI Worker Service for Video Processing" \
      org.opencontainers.image.source="https://github.com/nativity-ai/worker"

# Environment variables for worker configuration
ENV NODE_ENV=production \
    WORKER_CONCURRENCY=2 \
    MAX_PROCESSING_TIME=1800 \
    TEMP_DIR=/app/tmp \
    PROCESSING_DIR=/app/processing