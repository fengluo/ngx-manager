FROM nginx

# Update package lists and install necessary packages
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-yaml \
    python3-jinja2 \
    python3-watchdog \
    bash \
    curl \
    openssl \
    socat \
    coreutils \
    dnsutils \
    tzdata \
    cron \
    procps \
    && rm -rf /var/lib/apt/lists/*

# Install acme.sh
RUN curl https://get.acme.sh | sh -s email=admin@example.com \
    && ln -s /root/.acme.sh/acme.sh /usr/local/bin/acme.sh

# Create application directory structure
RUN mkdir -p /app/{config,templates,scripts,logs} \
    && mkdir -p /var/www/{html,static,uploads} \
    && mkdir -p /etc/nginx/ssl

# Copy application files
COPY templates/ /app/templates/
COPY scripts/ /app/scripts/
COPY config/nginx.conf /etc/nginx/nginx.conf

# Set script execution permissions
RUN chmod +x /app/scripts/*.py

# Create default configuration directory
RUN mkdir -p /etc/nginx/conf.d

# Set working directory
WORKDIR /app

# Expose ports
EXPOSE 80 443

# Set environment variables
ENV TZ=Asia/Shanghai
ENV NGINX_RELOAD_SIGNAL=HUP
ENV ACME_HOME=/root/.acme.sh

# Startup script
CMD ["/usr/bin/python3", "/app/scripts/entrypoint.py"] 