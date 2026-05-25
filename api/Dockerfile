# Multi-stage Dockerfile for Nativity.AI API Service
# Optimized for production deployment on AWS ECS Fargate

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

# Stage 2: Production stage
FROM node:18-alpine AS production

# Install security updates
RUN apk update && apk upgrade && apk add --no-cache dumb-init

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

# Create necessary directories
RUN mkdir -p logs tmp && chown -R nativity:nodejs logs tmp

# Switch to non-root user
USER nativity

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD node healthcheck.js || exit 1

# Use dumb-init to handle signals properly
ENTRYPOINT ["dumb-init", "--"]

# Start the application
CMD ["node", "server.js"]

# Labels for better container management
LABEL maintainer="Nativity.AI Team" \
      version="1.0.0" \
      description="Nativity.AI API Service" \
      org.opencontainers.image.source="https://github.com/nativity-ai/api"