FROM nginx:alpine

# Install Python and required packages
RUN apk add --no-cache \
    python3 \
    py3-pip \
    py3-yaml \
    bash \
    curl \
    openssl \
    socat \
    tzdata \
    dcron \
    procps \
    && rm -rf /var/cache/apk/*

# Install acme.sh
RUN curl https://get.acme.sh | sh -s email=test@gmail.com \
    && ln -s /root/.acme.sh/acme.sh /usr/local/bin/acme.sh

# Create application directory structure
RUN mkdir -p /app/{config,logs,certs} \
    && mkdir -p /var/www/{html,static,uploads} \
    && mkdir -p /etc/nginx/ssl

# Set working directory
WORKDIR /app

# Copy Python application
COPY requirements.txt /app/
COPY nginx_manager/ /app/nginx_manager/
COPY setup.py /app/
COPY nginx_manager.py /app/

# Create virtual environment and install Python dependencies
RUN python3 -m venv /app/venv \
    && /app/venv/bin/pip install --no-cache-dir -r requirements.txt \
    && /app/venv/bin/pip install -e .

# Make sure venv binaries are in PATH
ENV PATH="/app/venv/bin:$PATH"

# Copy configuration files
COPY config/nginx.conf /etc/nginx/nginx.conf
COPY config/ /app/config/

# Copy entrypoint script
COPY docker-entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Expose ports
EXPOSE 80 443

# Set environment variables
ENV TZ=Asia/Shanghai
ENV NGINX_RELOAD_SIGNAL=HUP
ENV ACME_HOME=/root/.acme.sh

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost/ || exit 1

# Start container
CMD ["/app/entrypoint.sh"] 