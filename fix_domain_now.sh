#!/bin/bash
# Quick domain configuration fix script

DOMAIN="prezentacje.soft-synergy.com"
APP_PORT=5001
SERVER_IP=$(hostname -I | awk '{print $1}')

echo "===== FIXING DOMAIN CONFIGURATION FOR $DOMAIN ====="
echo "Server IP: $SERVER_IP"
echo "Application port: $APP_PORT"

# Check if Nginx is installed
if ! command -v nginx &> /dev/null; then
    echo "Installing Nginx..."
    sudo apt-get update
    sudo apt-get install -y nginx
fi

# Create directory for application files if they don't exist
echo "Creating required directories..."
SCRIPT_DIR=$(dirname "$(readlink -f "$0")")
mkdir -p "$SCRIPT_DIR/static"
mkdir -p "$SCRIPT_DIR/avatars"
mkdir -p "$SCRIPT_DIR/presentations"

# Create a simple Nginx configuration with minimal settings
echo "Creating Nginx configuration..."
cat << EOF > "$SCRIPT_DIR/prezentacje.conf"
server {
    listen 80;
    server_name $DOMAIN;

    access_log /var/log/nginx/prezentacje-access.log;
    error_log /var/log/nginx/prezentacje-error.log;

    location / {
        proxy_pass http://127.0.0.1:$APP_PORT;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    location /static/ {
        alias $SCRIPT_DIR/static/;
        expires 30d;
    }

    location /avatars/ {
        alias $SCRIPT_DIR/avatars/;
        expires 7d;
    }

    location /presentations/ {
        alias $SCRIPT_DIR/presentations/;
        expires 1d;
    }
}
EOF

# Install the configuration
echo "Installing Nginx configuration..."
sudo cp "$SCRIPT_DIR/prezentacje.conf" /etc/nginx/sites-available/prezentacje.conf
sudo ln -sf /etc/nginx/sites-available/prezentacje.conf /etc/nginx/sites-enabled/

# Remove default site if it exists to avoid conflicts
if [ -f "/etc/nginx/sites-enabled/default" ]; then
    echo "Disabling default Nginx site..."
    sudo rm -f /etc/nginx/sites-enabled/default
fi

# Test and reload Nginx
echo "Testing Nginx configuration..."
if sudo nginx -t; then
    echo "Nginx configuration is valid. Reloading..."
    sudo systemctl reload nginx
else
    echo "Nginx configuration test failed. Fixing common issues..."
    # Try to fix common configuration issues
    sudo sed -i 's/\r$//' /etc/nginx/sites-available/prezentacje.conf  # Remove Windows line endings
    
    # Test again
    if sudo nginx -t; then
        echo "Fixed Nginx configuration. Reloading..."
        sudo systemctl reload nginx
    else
        echo "Nginx configuration still has errors. Manual intervention required."
    fi
fi

# Open firewall ports
echo "Opening firewall ports..."
if command -v ufw &> /dev/null; then
    sudo ufw allow 80/tcp
    sudo ufw allow 443/tcp
    sudo ufw allow $APP_PORT/tcp
else
    # Use iptables directly if ufw is not installed
    sudo iptables -A INPUT -p tcp --dport 80 -j ACCEPT
    sudo iptables -A INPUT -p tcp --dport 443 -j ACCEPT
    sudo iptables -A INPUT -p tcp --dport $APP_PORT -j ACCEPT
fi

# Restart the Flask application
echo "Checking Flask application..."
FLASK_PROCESSES=$(ps aux | grep "python app.py" | grep -v grep | awk '{print $2}')
if [ -n "$FLASK_PROCESSES" ]; then
    echo "Flask application is already running. Restarting..."
    for PID in $FLASK_PROCESSES; do
        kill -9 $PID
    done
fi

# Try to restart using systemd service first
FLASK_SERVICE_PATH="/etc/systemd/system/prezentacje-flask.service"
if [ -f "$FLASK_SERVICE_PATH" ]; then
    echo "Updating and restarting Flask service..."
    sudo systemctl daemon-reload
    sudo systemctl restart prezentacje-flask
    sudo systemctl status prezentacje-flask
else
    # If no service exists, create one
    echo "Creating Flask systemd service..."
    cat << EOF > "$SCRIPT_DIR/prezentacje-flask.service"
[Unit]
Description=Prezentacje Flask Application
After=network.target

[Service]
User=$(whoami)
Group=$(id -gn)
WorkingDirectory=$SCRIPT_DIR
Environment="PATH=$SCRIPT_DIR/venv/bin:/usr/local/bin:/usr/bin:/bin"
Environment="APP_DOMAIN=$DOMAIN"
ExecStart=/usr/bin/python3 $SCRIPT_DIR/app.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF
    
    sudo cp "$SCRIPT_DIR/prezentacje-flask.service" /etc/systemd/system/
    sudo systemctl daemon-reload
    sudo systemctl enable prezentacje-flask
    sudo systemctl start prezentacje-flask
    sudo systemctl status prezentacje-flask
fi

echo ""
echo "===== CONFIGURATION COMPLETE ====="
echo "Domain: $DOMAIN"
echo "Server IP: $SERVER_IP"
echo "App port: $APP_PORT"
echo ""
echo "You should now be able to access your site at: http://$DOMAIN/"
echo ""
echo "If the site is still not accessible, please check:"
echo "1. DNS settings - Make sure domain points to $SERVER_IP"
echo "2. Flask application logs: sudo journalctl -u prezentacje-flask -f"
echo "3. Nginx logs: sudo tail -f /var/log/nginx/prezentacje-error.log"
echo ""
echo "Testing domain accessibility (this may not work if DNS has not propagated):"
curl -I http://$DOMAIN/ 2>/dev/null || echo "Domain not yet accessible or DNS not propagated" 