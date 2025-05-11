#!/bin/bash
# Script to add Let's Encrypt SSL to prezentacje.soft-synergy.com

DOMAIN="prezentacje.soft-synergy.com"

echo "===== ADDING LET'S ENCRYPT SSL FOR $DOMAIN ====="

# Check if running as root
if [ "$EUID" -ne 0 ]; then
  echo "Please run as root (use sudo)"
  exit 1
fi

# Install certbot and the Nginx plugin if not already installed
echo "Installing Certbot..."
apt-get update
apt-get install -y certbot python3-certbot-nginx

# Check if Nginx is installed and running
if ! systemctl is-active --quiet nginx; then
    echo "Nginx is not running. Starting Nginx..."
    systemctl start nginx
fi

# Ensure the Nginx configuration for the domain exists
NGINX_CONF_PATH="/etc/nginx/sites-available/prezentacje.conf"
if [ ! -f "$NGINX_CONF_PATH" ]; then
    echo "ERROR: Nginx configuration for $DOMAIN not found at $NGINX_CONF_PATH"
    echo "Please run fix_domain_now.sh first to set up the domain."
    exit 1
fi

# Make sure the domain is enabled in Nginx
if [ ! -f "/etc/nginx/sites-enabled/prezentacje.conf" ]; then
    echo "Enabling domain in Nginx..."
    ln -sf "$NGINX_CONF_PATH" /etc/nginx/sites-enabled/
    nginx -t && systemctl reload nginx
fi

# Obtain and install SSL certificate
echo "Obtaining Let's Encrypt SSL certificate for $DOMAIN..."
certbot --nginx -d $DOMAIN --non-interactive --agree-tos --email admin@$DOMAIN --redirect

# Check if certificate was installed successfully
if [ $? -eq 0 ]; then
    echo "SSL certificate installed successfully!"
    
    # Verify Nginx configuration
    nginx -t
    
    # Reload Nginx to apply changes
    systemctl reload nginx
    
    # Display certificate information
    echo ""
    echo "Certificate information:"
    certbot certificates
    
    echo ""
    echo "===== SSL SETUP COMPLETE ====="
    echo "Your site is now available at: https://$DOMAIN"
    echo ""
    echo "Certificate will auto-renew via the installed cron job."
    echo "You can test the renewal process with: certbot renew --dry-run"
else
    echo "Failed to install SSL certificate."
    echo "Possible issues:"
    echo "1. Domain DNS may not be fully propagated yet"
    echo "2. Domain may not be pointing to this server"
    echo "3. Firewall might be blocking port 80/443"
    
    # Check DNS resolution
    echo ""
    echo "Checking DNS resolution..."
    host $DOMAIN || echo "Domain is not resolving properly"
    
    # Check firewall for ports 80 and 443
    echo ""
    echo "Checking firewall status..."
    if command -v ufw &> /dev/null; then
        ufw status | grep -E "80|443" || echo "Ports 80/443 might not be open in firewall"
        echo "To open ports: ufw allow 80/tcp && ufw allow 443/tcp"
    else
        iptables -L -n | grep -E "dpt:80|dpt:443" || echo "Ports 80/443 might not be open in firewall"
    fi
    
    echo ""
    echo "You can try manual setup with: certbot --nginx -d $DOMAIN"
fi

# Create an SSL redirect helper script for future use
cat > /usr/local/bin/force-ssl-$DOMAIN.sh << 'EOF'
#!/bin/bash
# Script to force SSL for domain
DOMAIN="prezentacje.soft-synergy.com"
NGINX_CONF="/etc/nginx/sites-available/prezentacje.conf"

# Add redirect from HTTP to HTTPS if not already present
if ! grep -q "return 301 https" $NGINX_CONF; then
    sed -i '/server {/,/listen 80/c\server {\n    listen 80;\n    server_name '"$DOMAIN"';\n    return 301 https://$host$request_uri;' $NGINX_CONF
    nginx -t && systemctl reload nginx
    echo "Added HTTP to HTTPS redirect for $DOMAIN"
else
    echo "HTTP to HTTPS redirect already configured"
fi
EOF

chmod +x /usr/local/bin/force-ssl-$DOMAIN.sh
echo "Created SSL helper script: /usr/local/bin/force-ssl-$DOMAIN.sh" 