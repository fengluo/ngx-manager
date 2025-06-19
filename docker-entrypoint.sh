#!/bin/bash

# Enable strict error handling
set -euo pipefail

# =============================================================================
# Configuration and Environment Setup
# =============================================================================

# Set default timezone
export TZ="${TZ:-Asia/Shanghai}"

# ACME.sh configuration
export ACME_HOME="/root/.acme.sh"
export LE_WORKING_DIR="/root/.acme.sh"

# Nginx configuration
NGINX_PID=""
HEALTH_CHECK_INTERVAL="${HEALTH_CHECK_INTERVAL:-10}"

# =============================================================================
# Utility Functions
# =============================================================================

# Logging function with timestamp
log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $*"
}

# Error logging function
log_error() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: $*" >&2
}

# =============================================================================
# Initialization Functions
# =============================================================================

# Initialize required directories
init_directories() {
    log "Initializing directory structure..."
    
    local directories=(
        "/app/config"
        "/app/logs" 
        "/app/certs"
        "/var/www/html"
        "/var/www/html/.well-known/acme-challenge"
        "/etc/nginx/conf.d"
        "/etc/nginx/ssl"
    )
    
    for dir in "${directories[@]}"; do
        if ! mkdir -p "$dir"; then
            log_error "Failed to create directory: $dir"
            exit 1
        fi
    done
    
    log "Directory structure initialized successfully"
}

# Set up proper permissions
setup_permissions() {
    log "Setting up file permissions..."
    
    # Set permissions for ACME challenge directory
    if ! chmod 755 /var/www/html/.well-known/acme-challenge; then
        log_error "Failed to set permissions for ACME challenge directory"
        exit 1
    fi
    
    # Change ownership to nginx user
    if ! chown -R nginx:nginx /var/www/; then
        log_error "Failed to change ownership of /var/www/"
        exit 1
    fi
    
    log "Permissions set up successfully"
}

# =============================================================================
# Nginx Management Functions
# =============================================================================

# Start nginx process
start_nginx() {
    log "Starting Nginx..."
    
    # Test nginx configuration first
    if ! nginx -t; then
        log_error "Nginx configuration test failed"
        exit 1
    fi
    
    # Start nginx in background
    nginx -g "daemon off;" &
    NGINX_PID=$!
    
    # Verify nginx started successfully
    if ! kill -0 "$NGINX_PID" 2>/dev/null; then
        log_error "Failed to start Nginx"
        exit 1
    fi
    
    log "Nginx started successfully with PID: $NGINX_PID"
}

# Check if nginx is running
is_nginx_running() {
    [[ -n "$NGINX_PID" ]] && kill -0 "$NGINX_PID" 2>/dev/null
}

# Restart nginx if it's not running
ensure_nginx_running() {
    if ! is_nginx_running; then
        log "Nginx process died, restarting..."
        start_nginx
    fi
}

# =============================================================================
# Signal Handling
# =============================================================================

# Graceful shutdown handler
graceful_shutdown() {
    log "Received shutdown signal, initiating graceful shutdown..."
    
    if [[ -n "$NGINX_PID" ]] && kill -0 "$NGINX_PID" 2>/dev/null; then
        log "Stopping Nginx (PID: $NGINX_PID)..."
        
        # Send TERM signal to nginx
        kill -TERM "$NGINX_PID" 2>/dev/null || true
        
        # Wait for nginx to stop gracefully (max 30 seconds)
        local timeout=30
        while [[ $timeout -gt 0 ]] && kill -0 "$NGINX_PID" 2>/dev/null; do
            sleep 1
            ((timeout--))
        done
        
        # Force kill if still running
        if kill -0 "$NGINX_PID" 2>/dev/null; then
            log "Force killing Nginx..."
            kill -KILL "$NGINX_PID" 2>/dev/null || true
        fi
        
        # Wait for process to actually terminate
        wait "$NGINX_PID" 2>/dev/null || true
        log "Nginx stopped successfully"
    fi
    
    log "Shutdown complete"
    exit 0
}

# =============================================================================
# Main Execution
# =============================================================================

main() {
    log "Starting Nginx Manager container..."
    
    # Initialize environment
    init_directories
    setup_permissions
    
    # Set up signal handlers for graceful shutdown
    trap graceful_shutdown SIGTERM SIGINT SIGQUIT
    
    # Start nginx
    start_nginx
    
    # Main supervision loop
    log "Entering supervision loop (health check interval: ${HEALTH_CHECK_INTERVAL}s)"
    while true; do
        ensure_nginx_running
        sleep "$HEALTH_CHECK_INTERVAL"
    done
}

# Start main execution
main "$@" 