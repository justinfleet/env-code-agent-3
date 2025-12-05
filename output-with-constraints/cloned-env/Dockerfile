FROM node:20-slim

# Enable corepack for pnpm
RUN corepack enable

# Install pnpm globally with specific version
RUN corepack prepare pnpm@9.15.1 --activate

WORKDIR /app

# Copy package files
COPY package.json pnpm-workspace.yaml ./
COPY server/package.json server/
COPY data/ data/

# Install dependencies
RUN pnpm install --frozen-lockfile

# Copy source code
COPY server/ server/

# Build the application
RUN pnpm --filter server build

# Expose port
EXPOSE 3002

# Start the server
CMD ["pnpm", "--filter", "server", "start"]