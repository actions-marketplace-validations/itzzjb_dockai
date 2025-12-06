# ---- Stage 1: Builder ----
FROM node:25.2.1-alpine3.23 AS builder

WORKDIR /app
# Ensure the app directory is writable by the non-root user
RUN chown -R node:node /app

# Copy manifests first for better layer caching
COPY --chown=node:node package*.json ./

# Install production dependencies as non-root; fall back if lockfile mismatch
USER node
RUN npm ci --omit=dev --no-audit --no-fund || npm install --omit=dev --no-audit --no-fund

# Copy only required source files
COPY --chown=node:node server.js ./

# Extra safety to keep only production deps
RUN npm prune --omit=dev


# ---- Stage 2: Runtime ----
FROM node:25.2.1-alpine3.23

ENV NODE_ENV=production PORT=3000
WORKDIR /app

# Copy runtime artifacts
COPY --from=builder --chown=node:node /app/node_modules ./node_modules
COPY --from=builder --chown=node:node /app/package.json ./package.json
COPY --from=builder --chown=node:node /app/server.js ./server.js

EXPOSE 3000

# Use busybox wget for healthcheck; respect overridable PORT
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD ["sh","-c","wget -q -O- http://127.0.0.1:${PORT:-3000}/health || exit 1"]

# Run as non-root
USER node

# Start the service
CMD ["node","server.js"]
