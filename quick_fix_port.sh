#!/bin/bash
# Quick script to fix port 5001 conflict by changing to port 5002

OLD_PORT=5001
NEW_PORT=5002

echo "==== Quick fix: Changing Flask app from port $OLD_PORT to port $NEW_PORT ===="

# Update app.py
if [ -f "app.py" ]; then
    echo "Updating app.py..."
    sed -i.bak "s/port=$OLD_PORT/port=$NEW_PORT/g" app.py
    echo "Updated app.py to use port $NEW_PORT"
else
    echo "ERROR: app.py not found in current directory."
    exit 1
fi

# Update Nginx configuration
NGINX_CONF_PATH="/etc/nginx/sites-available/prezentacje.conf"
if [ -f "$NGINX_CONF_PATH" ]; then
    echo "Updating Nginx configuration..."
    sudo cp "$NGINX_CONF_PATH" "${NGINX_CONF_PATH}.bak"
    sudo sed -i "s/127.0.0.1:$OLD_PORT/127.0.0.1:$NEW_PORT/g" "$NGINX_CONF_PATH"
    
    echo "Testing Nginx configuration..."
    if sudo nginx -t; then
        echo "Nginx configuration is valid. Reloading..."
        sudo systemctl reload nginx
    else
        echo "Nginx configuration test failed. Reverting to backup..."
        sudo cp "${NGINX_CONF_PATH}.bak" "$NGINX_CONF_PATH"
        exit 1
    fi
else
    echo "WARNING: Nginx configuration file not found at $NGINX_CONF_PATH."
    echo "You will need to manually update your Nginx configuration to proxy to port $NEW_PORT."
fi

# Kill any existing Flask processes
echo "Checking for existing Flask processes..."
FLASK_PROCESSES=$(ps aux | grep "python app.py" | grep -v grep | awk '{print $2}')
if [ -n "$FLASK_PROCESSES" ]; then
    echo "Killing existing Flask processes..."
    for PID in $FLASK_PROCESSES; do
        echo "Killing process $PID..."
        kill -9 $PID
    done
fi

# Restart the Flask application
FLASK_SERVICE_PATH="/etc/systemd/system/prezentacje-flask.service"
if [ -f "$FLASK_SERVICE_PATH" ]; then
    echo "Updating Flask service configuration..."
    sudo cp "$FLASK_SERVICE_PATH" "${FLASK_SERVICE_PATH}.bak"
    sudo sed -i "s/python app.py/python app.py --port=$NEW_PORT/g" "$FLASK_SERVICE_PATH"
    
    echo "Restarting Flask application service..."
    sudo systemctl daemon-reload
    sudo systemctl restart prezentacje-flask
    sleep 2
    sudo systemctl status prezentacje-flask
else
    echo "Starting Flask application manually..."
    cd $(dirname "$0")
    nohup python app.py --port=$NEW_PORT > flask.log 2>&1 &
    echo "Flask application started with PID $! on port $NEW_PORT"
fi

echo ""
echo "Configuration changed to use port $NEW_PORT instead of port $OLD_PORT."
echo "Please access your application at: http://prezentacje.soft-synergy.com/"
echo ""
echo "To check if the application is running correctly, use:"
echo "  curl http://127.0.0.1:$NEW_PORT/" 