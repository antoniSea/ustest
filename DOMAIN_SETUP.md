# Domain Setup for prezentacje.soft-synergy.com

This guide will help you configure your server to run the application on the prezentacje.soft-synergy.com domain.

## Prerequisites

- A server with:
  - Nginx installed
  - Python 3.7+ installed
  - Systemd for service management
- Domain prezentacje.soft-synergy.com pointed to your server's IP address

## Installation Steps

### 1. Update Application Files

All necessary code changes have been made to the application in the repository.

### 2. Configure Nginx

1. Copy the Nginx configuration file to the proper location:

```bash
sudo cp nginx-prezentacje.conf /etc/nginx/sites-available/prezentacje.conf
```

2. Create a symbolic link to enable the site:

```bash
sudo ln -s /etc/nginx/sites-available/prezentacje.conf /etc/nginx/sites-enabled/
```

3. Edit the file to update the paths to your actual application directory:

```bash
sudo nano /etc/nginx/sites-available/prezentacje.conf
```

Replace `/path/to/your/app/` with your actual application path, for example: `/home/your_user/useme-bot/`

4. Test the Nginx configuration:

```bash
sudo nginx -t
```

5. Reload Nginx to apply changes:

```bash
sudo systemctl reload nginx
```

### 3. Set Up the Flask Application as a Service

1. Copy the systemd service file to the proper location:

```bash
sudo cp prezentacje-flask.service /etc/systemd/system/
```

2. Edit the service file to update paths and user information:

```bash
sudo nano /etc/systemd/system/prezentacje-flask.service
```

Replace:
- `your_user` and `your_group` with your actual system user and group
- `/path/to/your/app` with your actual application path

3. Reload systemd to recognize the new service:

```bash
sudo systemctl daemon-reload
```

4. Enable and start the service:

```bash
sudo systemctl enable prezentacje-flask
sudo systemctl start prezentacje-flask
```

5. Check status to make sure it's running:

```bash
sudo systemctl status prezentacje-flask
```

### 4. Firewall Configuration

If you have a firewall enabled (like UFW), make sure to allow HTTP traffic:

```bash
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
```

### 5. Testing the Setup

1. Access your domain in a web browser:
   http://prezentacje.soft-synergy.com/

2. Check the logs if you encounter issues:

```bash
# Nginx logs
sudo tail -f /var/log/nginx/prezentacje-error.log

# Flask application logs
sudo journalctl -u prezentacje-flask -f
```

## Optional: Set Up SSL with Let's Encrypt

For secure HTTPS connections, you can set up SSL:

```bash
sudo apt update
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d prezentacje.soft-synergy.com
```

Follow the prompts to complete SSL setup.

## Troubleshooting

- If the application doesn't start: Check the logs with `sudo journalctl -u prezentacje-flask -f`
- If Nginx returns a 502 Bad Gateway: Make sure the Flask application is running on port 5001
- If the domain doesn't resolve: Verify your DNS settings to ensure the domain points to your server IP 