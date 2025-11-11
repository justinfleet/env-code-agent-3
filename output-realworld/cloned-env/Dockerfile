# Use official Node.js runtime as base image
FROM node:20-alpine

# Install pnpm
RUN npm install -g pnpm@9.15.1

# Set working directory
WORKDIR /app

# Copy package files
COPY package.json pnpm-workspace.yaml ./
COPY server/package.json ./server/

# Install dependencies
RUN pnpm install --frozen-lockfile

# Copy source code
COPY server/ ./server/
COPY data/ ./data/

# Build the application
RUN pnpm build

# Expose the port
EXPOSE 3003

# Set production environment
ENV NODE_ENV=production
ENV PORT=3003

# Start the server
CMD ["pnpm", "start"]