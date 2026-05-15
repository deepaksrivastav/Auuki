# Stage 1: Build the React app
FROM node:22-alpine AS builder
WORKDIR /app

# Copy package files
COPY package.json package-lock.json* ./

# Install dependencies (ignoring scripts if they cause issues,
# but usually npm handles them fine)
RUN npm install

# Copy source and build
COPY . .
RUN npm run build

# Stage 2: Serve using Python
FROM python:3.11-slim-bookworm
WORKDIR /app

# Copy the compiled dist folder from the builder stage
COPY --from=builder /app/dist ./dist
COPY serve.py .


EXPOSE 3000

# Run the script instead of a messy one-liner
CMD ["python3", "serve.py"]