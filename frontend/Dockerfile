# =====================================
# Stage 1: Dependencies
# =====================================
FROM node:18-alpine AS deps

WORKDIR /app

# Copy package files
COPY package.json package-lock.json* ./

# Install all dependencies (use npm install for flexibility)
RUN npm install

# =====================================
# Stage 2: Builder
# =====================================
FROM node:18-alpine AS builder

WORKDIR /app

# Copy dependencies from deps stage
COPY --from=deps /app/node_modules ./node_modules
COPY . .

# Build the application
RUN npm run build

# =====================================
# Stage 3: Production Runner
# =====================================
FROM node:18-alpine AS runner

WORKDIR /app

# Install wget for healthcheck
RUN apk add --no-cache wget

# Create non-root user
RUN addgroup --system --gid 1001 nodejs \
    && adduser --system --uid 1001 svelte

# Copy package files and install production dependencies only
COPY package.json ./
RUN npm install --omit=dev

# Copy built application
COPY --from=builder --chown=svelte:nodejs /app/build ./build

# Switch to non-root user
USER svelte

# Expose port
EXPOSE 4173

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost:4173/ || exit 1

# Serve static files
CMD ["npx", "serve", "-s", "build", "-l", "4173"]
