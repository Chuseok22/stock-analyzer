FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    TZ=Asia/Seoul \
    PYTHONPATH=/app

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt

# Create non-root user
RUN addgroup --system stockanalyzer && adduser --system --ingroup stockanalyzer stockanalyzer

# Copy application code
COPY . .

# Create necessary directories and set permissions
RUN mkdir -p logs models features cache && \
    chown -R stockanalyzer:stockanalyzer /app

# Switch to non-root user
USER stockanalyzer

# Health check
HEALTHCHECK --interval=60s --timeout=30s --start-period=10s --retries=3 \
    CMD python -c "import sys; sys.exit(0)" || exit 1

# Expose port (for future web interface)
EXPOSE 8080

# Run the server
CMD ["python", "server.py", "--daemon"]