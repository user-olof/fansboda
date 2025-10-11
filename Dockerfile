# Use Python 3.11 slim image as base
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV FLASK_APP=app.py
ENV FLASK_ENV=production

# Set work directory
WORKDIR /app

# Create virtual environment
RUN python -m venv .venv

# Add virtual environment to PATH
ENV PATH="/app/.venv/bin:$PATH"

# Install system dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libc6-dev \
    libffi-dev \
    libssl-dev \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Install Python dependencies using virtual environment
RUN .venv/bin/pip install --no-cache-dir --upgrade pip \
    && .venv/bin/pip install --no-cache-dir -r requirements.txt \
    && .venv/bin/pip install --no-cache-dir gunicorn

# Create non-root user for security
RUN addgroup --system --gid 1001 appgroup \
    && adduser --system --uid 1001 --gid 1001 --no-create-home appuser

# Copy application code
COPY . .

# Create necessary directories and set permissions
RUN mkdir -p /app/instance /tmp/flask_session \
    && chown -R appuser:appgroup /app \
    && chmod -R 755 /app \
    && chown -R appuser:appgroup /tmp/flask_session \
    && chmod -R 755 /tmp/flask_session

# Switch to non-root user
USER appuser

# Expose port 8080
EXPOSE 8080

# Health check (updated for port 8080)
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/ || exit 1

# Run the application using virtual environment
CMD [".venv/bin/gunicorn", "--bind", "0.0.0.0:8080", "--workers", "4", "--timeout", "120", "app:app"]