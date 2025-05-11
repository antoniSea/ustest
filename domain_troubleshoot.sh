#!/bin/bash
# Domain troubleshooting script for prezentacje.soft-synergy.com

DOMAIN="prezentacje.soft-synergy.com"
APP_PORT=5001
SERVER_IP=$(hostname -I | awk '{print $1}')

echo "===== DOMAIN TROUBLESHOOTING FOR $DOMAIN ====="
echo "Local server IP: $SERVER_IP"
echo "Application port: $APP_PORT"
echo ""

# Check DNS resolution
echo "===== CHECKING DNS RESOLUTION ====="
echo "Local DNS resolution:"
host $DOMAIN || echo "Failed to resolve $DOMAIN locally"
echo ""

echo "External DNS resolution:"
echo "Resolving $DOMAIN to IP using Google DNS (8.8.8.8):"
dig @8.8.8.8 $DOMAIN +short || echo "Failed to resolve $DOMAIN with Google DNS"
echo ""

# Check Nginx configuration
echo "===== CHECKING NGINX CONFIGURATION ====="
echo "Checking if Nginx is installed:"
if command -v nginx &> /dev/null; then
    echo "Nginx is installed."
    
    echo "Checking Nginx status:"
    systemctl status nginx --no-pager || echo "Nginx service check failed"
    
    echo "Checking nginx.conf syntax:"
    nginx -t || echo "Nginx configuration test failed"
    
    echo "Checking if domain configuration exists:"
    NGINX_CONF_PATH="/etc/nginx/sites-available/prezentacje.conf"
    if [ -f "$NGINX_CONF_PATH" ]; then
        echo "Domain configuration found at $NGINX_CONF_PATH"
        echo "Configuration contents:"
        cat "$NGINX_CONF_PATH"
        
        echo "Checking if site is enabled:"
        if [ -f "/etc/nginx/sites-enabled/prezentacje.conf" ]; then
            echo "Site is enabled in Nginx."
        else
            echo "ERROR: Site configuration exists but is not enabled!"
            echo "Run: sudo ln -s /etc/nginx/sites-available/prezentacje.conf /etc/nginx/sites-enabled/"
        fi
    else
        echo "ERROR: Domain configuration not found at $NGINX_CONF_PATH"
        echo "Create the configuration file:"
        echo "sudo cp nginx-prezentacje.conf $NGINX_CONF_PATH"
        echo "sudo ln -s $NGINX_CONF_PATH /etc/nginx/sites-enabled/"
    fi
else
    echo "ERROR: Nginx is not installed. Install with: sudo apt-get install nginx"
fi
echo ""

# Check application accessibility
echo "===== CHECKING APPLICATION ACCESSIBILITY ====="
echo "Checking if application is accessible on localhost:$APP_PORT:"
curl -s -I http://localhost:$APP_PORT/ || echo "Failed to connect to application on localhost:$APP_PORT"

echo "Checking if application is accessible on $SERVER_IP:$APP_PORT:"
curl -s -I http://$SERVER_IP:$APP_PORT/ || echo "Failed to connect to application on $SERVER_IP:$APP_PORT"

echo "Checking if application is accessible via domain (locally):"
curl -s -I --resolve $DOMAIN:80:127.0.0.1 http://$DOMAIN/ || echo "Failed to connect to domain (locally resolved)"
echo ""

# Check firewall configuration
echo "===== CHECKING FIREWALL CONFIGURATION ====="
echo "Checking if firewall is enabled:"
if command -v ufw &> /dev/null; then
    echo "UFW firewall status:"
    ufw status || echo "Failed to get UFW status"
else
    echo "UFW not installed. Checking iptables rules:"
    iptables -L -n || echo "Failed to list iptables rules"
fi

echo "Checking if ports 80 and $APP_PORT are open:"
netstat -tuln | grep -E ":80|:$APP_PORT" || echo "Ports 80 or $APP_PORT not listening"
echo ""

# Perform SSL check if domain uses HTTPS
echo "===== CHECKING SSL CONFIGURATION ====="
if curl -s -I https://$DOMAIN/ &> /dev/null; then
    echo "Domain appears to use HTTPS."
    echo "SSL certificate information:"
    echo | openssl s_client -servername $DOMAIN -connect $DOMAIN:443 2>/dev/null | openssl x509 -text -noout | grep -E "Subject:|Issuer:|Not Before:|Not After :|DNS:" || echo "Failed to retrieve SSL info"
else
    echo "Domain does not appear to use HTTPS or certificate is invalid."
fi
echo ""

# Server logs check
echo "===== CHECKING SERVER LOGS ====="
echo "Last 10 lines of Nginx error log:"
NGINX_ERROR_LOG="/var/log/nginx/prezentacje-error.log"
if [ -f "$NGINX_ERROR_LOG" ]; then
    tail -n 10 "$NGINX_ERROR_LOG" || echo "Failed to read Nginx error log"
else
    echo "Nginx error log not found at $NGINX_ERROR_LOG"
    echo "Checking default error log location:"
    tail -n 10 /var/log/nginx/error.log || echo "Failed to read default error log"
fi

echo "Last 10 lines of Nginx access log:"
NGINX_ACCESS_LOG="/var/log/nginx/prezentacje-access.log"
if [ -f "$NGINX_ACCESS_LOG" ]; then
    tail -n 10 "$NGINX_ACCESS_LOG" || echo "Failed to read Nginx access log"
else
    echo "Nginx access log not found at $NGINX_ACCESS_LOG"
    echo "Checking default access log location:"
    tail -n 10 /var/log/nginx/access.log || echo "Failed to read default access log"
fi
echo ""

# Fix recommendations
echo "===== RECOMMENDED FIXES ====="
echo "Based on common issues, here are some recommended fixes:"
echo ""
echo "1. If DNS resolution failed:"
echo "   - Verify domain DNS settings point to $SERVER_IP"
echo "   - It may take up to 24-48 hours for DNS changes to propagate globally"
echo ""
echo "2. If Nginx configuration is missing:"
echo "   - Run: sudo cp nginx-prezentacje.conf /etc/nginx/sites-available/prezentacje.conf"
echo "   - Run: sudo ln -s /etc/nginx/sites-available/prezentacje.conf /etc/nginx/sites-enabled/"
echo "   - Run: sudo nginx -t && sudo systemctl reload nginx"
echo ""
echo "3. If application isn't accessible locally:"
echo "   - Check if the Flask application is running: ps aux | grep app.py"
echo "   - Try restarting the Flask application with: .quick_fix_port.sh"
echo ""
echo "4. If firewall is blocking access:"
echo "   - Allow HTTP traffic: sudo ufw allow 80/tcp"
echo "   - Allow application port: sudo ufw allow $APP_PORT/tcp"
echo ""
echo "5. Create a quick fix for Nginx configuration:"
cat << 'EOF' > fix_nginx_config.sh
#!/bin/bash
# Quick Nginx configuration fix

DOMAIN="prezentacje.soft-synergy.com"
SERVER_IP=$(hostname -I | awk '{print $1}')
APP_PORT=5001

echo "Creating proper Nginx configuration for $DOMAIN..."

# Create updated configuration file
cat << 'CONF' > prezentacje.conf
server {
    listen 80;
    server_name prezentacje.soft-synergy.com;

    access_log /var/log/nginx/prezentacje-access.log;
    error_log /var/log/nginx/prezentacje-error.log;

    location / {
        proxy_pass http://127.0.0.1:5001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /static/ {
        alias /path/to/your/app/static/;
        expires 30d;
    }

    location /avatars/ {
        alias /path/to/your/app/avatars/;
        expires 7d;
    }

    location /presentations/ {
        alias /path/to/your/app/presentations/;
        expires 1d;
    }
}
CONF

# Replace path placeholders with actual paths
SCRIPT_DIR=$(dirname "$(readlink -f "$0")")
sed -i "s|/path/to/your/app|$SCRIPT_DIR|g" prezentacje.conf

# Install the configuration
sudo cp prezentacje.conf /etc/nginx/sites-available/prezentacje.conf
sudo ln -sf /etc/nginx/sites-available/prezentacje.conf /etc/nginx/sites-enabled/

# Test and reload Nginx
echo "Testing Nginx configuration..."
sudo nginx -t

if [ $? -eq 0 ]; then
    echo "Nginx configuration is valid. Reloading..."
    sudo systemctl reload nginx
else
    echo "Nginx configuration test failed. Please check the syntax errors above."
    exit 1
fi

echo "Nginx configuration updated for $DOMAIN"
echo "Check if the site is accessible now"
EOF

chmod +x fix_nginx_config.sh
echo "Created fix_nginx_config.sh - Run this script to create a proper Nginx configuration"
echo ""

# Final summary
echo "===== TROUBLESHOOTING SUMMARY ====="
echo "Domain: $DOMAIN"
echo "Server IP: $SERVER_IP"
echo "App port: $APP_PORT"
echo ""
echo "Next steps:"
echo "1. Review the output above for errors"
echo "2. Run fix scripts as needed"
echo "3. After making changes, try accessing http://$DOMAIN/ again"
echo "4. If still not working, check if application is running with 'ps aux | grep app.py'"
echo ""
echo "For more detailed Nginx troubleshooting, run: sudo nginx -T" 