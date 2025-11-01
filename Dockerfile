# Dockerfile for NIGHT Token Miner
# Multi-stage build for smaller final image

# Build stage
FROM rust:1.75-slim as builder

# Install build dependencies
RUN apt-get update && \
    apt-get install -y pkg-config libssl-dev git && \
    rm -rf /var/lib/apt/lists/*

# Create app directory
WORKDIR /app

# Copy project files
COPY Cargo.toml Cargo.lock ./
COPY src ./src
COPY benches ./benches
COPY examples ./examples

# Build the release binary
RUN cargo build --release

# Runtime stage
FROM debian:bookworm-slim

# Install runtime dependencies
RUN apt-get update && \
    apt-get install -y ca-certificates libssl3 && \
    rm -rf /var/lib/apt/lists/*

# Create app directory
WORKDIR /app

# Copy the binary from builder
COPY --from=builder /app/target/release/night-miner /usr/local/bin/night-miner

# Create wallet directory
RUN mkdir -p /app/auto-mine-wallet

# Set wallet directory as volume
VOLUME ["/app/auto-mine-wallet"]

# Run the miner
ENTRYPOINT ["night-miner"]
CMD ["auto-mine"]
