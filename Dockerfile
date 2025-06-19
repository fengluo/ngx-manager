# =============================================================================
# Nginx Manager - Multi-stage Docker Build
# =============================================================================

FROM nginx:alpine

# =============================================================================
# Build Arguments and Environment Variables
# =============================================================================

ARG ACME_EMAIL=test@gmail.com
ARG TZ=Asia/Shanghai

ENV TZ=${TZ} \
    NGINX_RELOAD_SIGNAL=HUP \
    ACME_HOME=/root/.acme.sh \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# =============================================================================
# System Dependencies Installation
# =============================================================================

# Install system packages and clean up in single layer
RUN apk add --no-cache \
        # Python runtime and package management
        python3 \
        py3-pip \
        py3-yaml \
        # Shell and system utilities
        bash \
        curl \
        procps \
        # SSL/TLS and networking
        openssl \
        socat \
        # System services
        tzdata \
        dcron \
    # Clean up package cache to reduce image size
    && rm -rf /var/cache/apk/* /tmp/* /var/tmp/*

# =============================================================================
# ACME.sh Installation and Configuration  
# =============================================================================

# Install acme.sh with proper configuration
RUN curl -fsSL https://get.acme.sh | sh -s email=${ACME_EMAIL} \
    && ln -sf /root/.acme.sh/acme.sh /usr/local/bin/acme.sh \
    # Set up cron job for certificate renewal
    && echo "30 2 * * * /root/.acme.sh/acme.sh --cron --home /root/.acme.sh > /app/logs/acme-cron.log 2>&1" \
        > /var/spool/cron/crontabs/root \
    && chmod 600 /var/spool/cron/crontabs/root

# =============================================================================
# Directory Structure Setup
# =============================================================================

# Create required directory structure in optimal order
RUN mkdir -p \
        # Application directories
        /app/config \
        /app/logs \
        /app/certs \
        # Web server directories
        /var/www/html \
        /var/www/static \
        /var/www/uploads \
        # Nginx configuration directories
        /etc/nginx/conf.d \
        /etc/nginx/ssl

# =============================================================================
# Application Installation
# =============================================================================

# Set working directory
WORKDIR /app

# Copy Python requirements first for better Docker layer caching
COPY requirements.txt ./

# Install Python dependencies
RUN pip3 install --no-cache-dir --upgrade pip \
    && pip3 install --no-cache-dir -r requirements.txt

# Copy application source code
COPY nginx_manager/ ./nginx_manager/
COPY setup.py nginx_manager.py ./

# Install application in development mode
RUN pip3 install --no-cache-dir -e .

# =============================================================================
# Runtime Configuration
# =============================================================================

# Copy and set up entrypoint script
COPY docker-entrypoint.sh ./entrypoint.sh
RUN chmod +x ./entrypoint.sh

# =============================================================================
# Container Configuration
# =============================================================================

# Expose standard HTTP/HTTPS ports
EXPOSE 80 443

# Configure health check with improved parameters
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -fsSL http://localhost/ > /dev/null || exit 1

# =============================================================================
# Container Startup
# =============================================================================

# Use exec form for better signal handling
CMD ["sh", "-c", "crond -b && exec /app/entrypoint.sh"] 