FROM node:20-alpine

# Install pnpm
RUN corepack enable && corepack prepare pnpm@9.15.1 --activate

# Set working directory
WORKDIR /app

# Copy package files
COPY package.json pnpm-workspace.yaml ./
COPY server/package.json ./server/

# Install dependencies
RUN pnpm install --frozen-lockfile

# Copy source code
COPY . .

# Build the application
RUN pnpm build

# Expose port
EXPOSE 3002

# Start the application
CMD ["pnpm", "start"]