# Build stage
FROM python:3.12-slim AS builder

# Install system dependencies
RUN apt-get update && apt-get install -y gcc g++ curl && rm -rf /var/lib/apt/lists/*

# Install uv and move to a known location
RUN (curl -LsSf https://astral.sh/uv/install.sh | sh) && (cp /root/.cargo/bin/uv /usr/local/bin/uv || cp /root/.local/bin/uv /usr/local/bin/uv || echo "uv not found in expected locations")

# Set working directory
WORKDIR /app

# Copy dependency files
COPY pyproject.toml .
COPY README.md .

# Create virtual environment and install dependencies
RUN uv venv .venv
# First install google-genai explicitly
RUN uv pip install google-genai==1.25.0
# Then install the rest
RUN uv pip install -e . --no-cache-dir

# Runtime stage
FROM python:3.12-slim

# Install runtime dependencies
RUN apt-get update && apt-get install -y tesseract-ocr tesseract-ocr-por libgl1-mesa-glx libglib2.0-0 curl && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m -u 1000 aria

# Set working directory
WORKDIR /app

# Copy from builder
COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /usr/local/bin/uv /usr/local/bin/uv

# Copy application code
COPY app/ ./app/
COPY main.py .
COPY .env.example .
COPY gcloud-credentials.json .

# Set environment variable for Google credentials
ENV GOOGLE_APPLICATION_CREDENTIALS=/app/gcloud-credentials.json

# Set ownership
RUN chown -R aria:aria /app

# Switch to non-root user
USER aria

# Set Python path
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH=/app:$PYTHONPATH

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Default command
CMD ["python", "main.py"]
