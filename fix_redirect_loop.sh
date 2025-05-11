#!/bin/bash
# Script to fix the redirect loop issue for prezentacje.soft-synergy.com

echo "Fixing redirect loop issue for prezentacje.soft-synergy.com"

# Pull latest changes
echo "Pulling latest changes from repository..."
git pull

# Fix Nginx configuration
echo "Updating Nginx configuration..."
NGINX_CONF_PATH="/etc/nginx/sites-available/prezentacje.conf"
if [ -f "$NGINX_CONF_PATH" ]; then
    # Backup old configuration
    sudo cp "$NGINX_CONF_PATH" "${NGINX_CONF_PATH}.bak"
    echo "Backup created at ${NGINX_CONF_PATH}.bak"
    
    # Replace configuration with new one
    sudo cp nginx-prezentacje.conf "$NGINX_CONF_PATH"
    
    # Test Nginx configuration
    echo "Testing Nginx configuration..."
    sudo nginx -t
    
    if [ $? -eq 0 ]; then
        echo "Nginx configuration is valid. Reloading..."
        sudo systemctl reload nginx
    else
        echo "Nginx configuration test failed. Reverting to backup..."
        sudo cp "${NGINX_CONF_PATH}.bak" "$NGINX_CONF_PATH"
        sudo systemctl reload nginx
    fi
else
    echo "Nginx configuration file not found at $NGINX_CONF_PATH."
    echo "Please follow the instructions in DOMAIN_SETUP.md to set up Nginx properly."
fi

# Restart Flask application service
echo "Restarting Flask application service..."
FLASK_SERVICE_PATH="/etc/systemd/system/prezentacje-flask.service"
if [ -f "$FLASK_SERVICE_PATH" ]; then
    sudo systemctl restart prezentacje-flask
    sudo systemctl status prezentacje-flask
else
    echo "Flask service file not found at $FLASK_SERVICE_PATH."
    echo "Please follow the instructions in DOMAIN_SETUP.md to set up the systemd service properly."
    
    # If service isn't set up, try to find and kill the existing Flask process
    echo "Attempting to find and restart Flask process manually..."
    PID=$(ps aux | grep "python app.py" | grep -v grep | awk '{print $2}')
    if [ -n "$PID" ]; then
        echo "Found Flask process with PID $PID. Killing..."
        kill -9 $PID
        echo "Starting Flask application..."
        cd $(dirname "$0")
        nohup python app.py > flask.log 2>&1 &
        echo "Flask application started with PID $!"
    else
        echo "No running Flask process found."
    fi
fi

echo "Fix completed. Please test accessing prezentacje.soft-synergy.com in your browser."
echo "If the issue persists, please check the logs:"
echo "- Flask logs: journalctl -u prezentacje-flask -f"
echo "- Nginx error logs: tail -f /var/log/nginx/prezentacje-error.log"

# Clear browser cache instructions
echo "
IMPORTANT: Remember to clear your browser cache:
- Chrome: press Ctrl+Shift+Delete or Cmd+Shift+Delete (Mac)
- Firefox: press Ctrl+Shift+Delete or Cmd+Shift+Delete (Mac)
- Safari: press Option+Command+E
" 