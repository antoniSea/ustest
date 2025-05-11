#!/bin/bash
# Script to fix port 5001 conflict

echo "==== Checking for processes using port 5001 ===="
PORT=5001

# Find processes using port 5001
PID_USING_PORT=$(lsof -i:$PORT -t 2>/dev/null)

if [ -n "$PID_USING_PORT" ]; then
    echo "Found process(es) using port $PORT:"
    for PID in $PID_USING_PORT; do
        PROCESS_INFO=$(ps -p $PID -o user,pid,cmd | tail -n +2)
        echo "$PROCESS_INFO"
    done
    
    echo ""
    echo "Options:"
    echo "1. Kill process(es) using port $PORT"
    echo "2. Change Flask application to use a different port"
    echo "3. Exit without making changes"
    
    read -p "Choose an option (1-3): " OPTION
    
    case $OPTION in
        1)
            echo "Killing process(es) using port $PORT..."
            for PID in $PID_USING_PORT; do
                echo "Killing process $PID..."
                sudo kill -9 $PID
            done
            echo "Process(es) killed. Checking if port is now available..."
            sleep 2
            if lsof -i:$PORT -t &>/dev/null; then
                echo "Port $PORT is still in use. Some processes couldn't be killed."
            else
                echo "Port $PORT is now available."
            fi
            ;;
        2)
            NEW_PORT=5002
            echo "Changing Flask application to use port $NEW_PORT..."
            
            # Update app.py
            if [ -f "app.py" ]; then
                echo "Updating app.py..."
                sed -i.bak "s/port=$PORT/port=$NEW_PORT/g" app.py
                echo "Updated app.py to use port $NEW_PORT"
                
                # Update Nginx configuration
                NGINX_CONF_PATH="/etc/nginx/sites-available/prezentacje.conf"
                if [ -f "$NGINX_CONF_PATH" ]; then
                    echo "Updating Nginx configuration..."
                    sudo sed -i.bak "s/127.0.0.1:$PORT/127.0.0.1:$NEW_PORT/g" "$NGINX_CONF_PATH"
                    echo "Updated Nginx configuration to proxy to port $NEW_PORT"
                    
                    # Test Nginx configuration
                    echo "Testing Nginx configuration..."
                    sudo nginx -t
                    
                    if [ $? -eq 0 ]; then
                        echo "Nginx configuration is valid. Reloading..."
                        sudo systemctl reload nginx
                    else
                        echo "Nginx configuration test failed. Reverting to backup..."
                        sudo cp "${NGINX_CONF_PATH}.bak" "$NGINX_CONF_PATH"
                    fi
                else
                    echo "Nginx configuration file not found at $NGINX_CONF_PATH."
                    echo "Please manually update your Nginx configuration to proxy to port $NEW_PORT."
                fi
            else
                echo "app.py not found in current directory. Please manually update your Flask application to use port $NEW_PORT."
            fi
            ;;
        3)
            echo "Exiting without making changes."
            exit 0
            ;;
        *)
            echo "Invalid option. Exiting without making changes."
            exit 1
            ;;
    esac
else
    echo "No process is using port $PORT."
fi

# Restart the Flask application if needed
FLASK_SERVICE_PATH="/etc/systemd/system/prezentacje-flask.service"
if [ -f "$FLASK_SERVICE_PATH" ]; then
    echo "Do you want to restart the Flask application service? (y/n)"
    read -p "> " RESTART
    if [[ "$RESTART" == "y" || "$RESTART" == "Y" ]]; then
        echo "Restarting Flask application service..."
        sudo systemctl restart prezentacje-flask
        sudo systemctl status prezentacje-flask
    fi
else
    echo "Flask service file not found at $FLASK_SERVICE_PATH."
    echo "To start Flask application manually, run:"
    echo "nohup python app.py > flask.log 2>&1 &"
fi

echo ""
echo "If you changed the port, remember to update any other configurations or scripts that refer to port $PORT." 