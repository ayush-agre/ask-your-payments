# ==============================================================================
# Production Dockerfile: Next.js Financial Studio Frontend
# Team CrackerX · Ask-Your-Payments FinOps Platform
# ==============================================================================

# ------------------------------------------------------------------------------
# Stage 1: Base image with pnpm package manager & user provisioning
# ------------------------------------------------------------------------------
FROM node:20-alpine AS base

# Install compatibility libraries and curl for health check
RUN apk add --no-cache libc6-compat curl
WORKDIR /app

# Create non-root system user early so it is consistently available in all stages
RUN addgroup --system --gid 1001 nodejs && \
    adduser --system --uid 1001 nextjs

# Configure pnpm store and bin path with wide write permissions
ENV PNPM_HOME="/pnpm"
ENV PATH="$PNPM_HOME:$PATH"
RUN mkdir -p /pnpm && chown -R nextjs:nodejs /pnpm && chmod -R 777 /pnpm

# Enable pnpm via corepack
RUN corepack enable && corepack prepare pnpm@12.18.0 --activate

# ------------------------------------------------------------------------------
# Stage 2: Install dependencies
# ------------------------------------------------------------------------------
FROM base AS deps
WORKDIR /app

# Copy dependency specifications
COPY package.json pnpm-lock.yaml* pnpm-workspace.yaml* ./

# Ensure working directory has correct ownership assigned to non-root user
# and full write permissions BEFORE pnpm install runs (fixes ERR_PNPM_LOCKFILE_WRITE_FILE)
RUN chown -R nextjs:nodejs /app && chmod -R 777 /app

# Execute pnpm install with sufficient (root) privileges before dropping to nextjs user
RUN pnpm install --frozen-lockfile

# Re-affirm correct ownership for installed node_modules and virtual store
RUN chown -R nextjs:nodejs /app

# ------------------------------------------------------------------------------
# Stage 3: Build the Next.js application
# ------------------------------------------------------------------------------
FROM base AS builder
WORKDIR /app

COPY --from=deps /app/node_modules ./node_modules
COPY . .

# Ensure working directory has correct ownership and write permissions before build
RUN chown -R nextjs:nodejs /app && chmod -R 775 /app

# Environment arguments for Next.js build-time inlining
ARG NEXT_PUBLIC_API_URL=http://localhost:8000
ARG NEXT_PUBLIC_WS_URL=ws://localhost:8000/ws/events
ARG NEXT_PUBLIC_AG_GRID_LICENSE_KEY=""

ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL \
    NEXT_PUBLIC_WS_URL=$NEXT_PUBLIC_WS_URL \
    NEXT_PUBLIC_AG_GRID_LICENSE_KEY=$NEXT_PUBLIC_AG_GRID_LICENSE_KEY \
    NEXT_TELEMETRY_DISABLED=1 \
    NODE_ENV=production

RUN pnpm run build

# ------------------------------------------------------------------------------
# Stage 4: Production Runner
# ------------------------------------------------------------------------------
FROM base AS runner
WORKDIR /app

ENV NODE_ENV=production \
    PORT=3000 \
    HOSTNAME="0.0.0.0" \
    NEXT_TELEMETRY_DISABLED=1

# Copy built application assets and production modules with non-root ownership
COPY --from=builder --chown=nextjs:nodejs /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next ./.next
COPY --from=builder --chown=nextjs:nodejs /app/node_modules ./node_modules
COPY --from=builder --chown=nextjs:nodejs /app/package.json ./package.json

# Explicitly ensure ownership of working directory before dropping to non-root user
RUN chown -R nextjs:nodejs /app

USER nextjs

EXPOSE 3000

# Health check to ensure frontend is serving HTTP requests
HEALTHCHECK --interval=20s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:3000/ || exit 1

# Explicitly expose host binding to 0.0.0.0 for public container interface
ENV HOSTNAME="0.0.0.0"
ENV PORT=3000

CMD ["pnpm", "start", "-p", "3000", "-H", "0.0.0.0"]
