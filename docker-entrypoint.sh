#!/bin/bash
set -e

# Set timezone
export TZ=${TZ:-Asia/Shanghai}

# Initialize directories
mkdir -p /app/{config,logs,certs}
mkdir -p /var/www/html
mkdir -p /etc/nginx/conf.d

# Set up acme.sh environment
export ACME_HOME=/root/.acme.sh
export LE_WORKING_DIR=/root/.acme.sh

# Create default acme challenge directory
mkdir -p /var/www/html/.well-known/acme-challenge

# Set permissions
chmod 755 /var/www/html/.well-known/acme-challenge
chown -R nginx:nginx /var/www/

# Start dcron for automatic certificate renewal
crond -b

# Function to start nginx
start_nginx() {
    echo "Starting nginx..."
    nginx -g "daemon off;" &
    NGINX_PID=$!
    echo "Nginx started with PID: $NGINX_PID"
}

# Function to handle signals
cleanup() {
    echo "Received signal, shutting down..."
    if [ ! -z "$NGINX_PID" ]; then
        kill $NGINX_PID
        wait $NGINX_PID
    fi
    exit 0
}

# Set up signal handlers
trap cleanup SIGTERM SIGINT

# Start nginx
start_nginx

# Keep container running and handle nginx-manager commands
while true; do
    # Check if nginx is still running
    if ! kill -0 $NGINX_PID 2>/dev/null; then
        echo "Nginx process died, restarting..."
        start_nginx
    fi
    
    # Sleep for a short interval
    sleep 10
done 