# HTTPS Setup with Let's Encrypt

This guide explains how to secure your prezentacje.soft-synergy.com domain with HTTPS using Let's Encrypt free SSL certificates.

## Automatic Installation

The easiest way to add SSL to your domain is to use the provided script:

```bash
sudo chmod +x add_ssl_letsencrypt.sh
sudo ./add_ssl_letsencrypt.sh
```

This script will:
1. Install Certbot and the Nginx plugin
2. Obtain and install an SSL certificate for your domain
3. Configure Nginx to use HTTPS
4. Set up automatic redirects from HTTP to HTTPS
5. Create a helper script for future SSL management

## Manual Installation

If you prefer to install SSL manually, follow these steps:

### 1. Install Certbot

```bash
sudo apt-get update
sudo apt-get install certbot python3-certbot-nginx
```

### 2. Obtain and Install SSL Certificate

```bash
sudo certbot --nginx -d prezentacje.soft-synergy.com
```

Follow the prompts to:
- Provide your email address (for renewal notifications)
- Agree to the terms of service
- Choose whether to redirect HTTP traffic to HTTPS

### 3. Verify the Installation

Check that your certificate was installed correctly:

```bash
sudo certbot certificates
```

Visit your site using HTTPS to ensure it works:
https://prezentacje.soft-synergy.com

## Certificate Renewal

Let's Encrypt certificates are valid for 90 days. Certbot installs a cron job that automatically attempts renewal for all certificates that are due to expire in less than 30 days.

To test the automatic renewal process:

```bash
sudo certbot renew --dry-run
```

## Troubleshooting

### If the certificate installation fails:

1. **DNS issues**: Make sure your domain correctly points to your server's IP address
   ```bash
   host prezentacje.soft-synergy.com
   ```

2. **Firewall blocking**: Ensure ports 80 and 443 are open
   ```bash
   sudo ufw allow 80/tcp
   sudo ufw allow 443/tcp
   ```

3. **Nginx configuration**: Check for syntax errors
   ```bash
   sudo nginx -t
   ```

4. **Let's Encrypt rate limits**: Be aware that Let's Encrypt has rate limits (5 certificates per domain per week)

### If the website doesn't load over HTTPS:

1. Check Nginx error logs:
   ```bash
   sudo tail -f /var/log/nginx/prezentacje-error.log
   ```

2. Verify the SSL certificate is correctly installed:
   ```bash
   sudo ls -la /etc/letsencrypt/live/prezentacje.soft-synergy.com/
   ```

3. Examine the Nginx SSL configuration:
   ```bash
   grep -r "ssl_certificate" /etc/nginx/sites-enabled/
   ```

## Security Enhancements

For enhanced security, consider these additional steps:

1. **Enable HTTP Strict Transport Security (HSTS)**:
   Edit your Nginx configuration to add:

   ```
   add_header Strict-Transport-Security "max-age=63072000; includeSubDomains; preload";
   ```

2. **Improve SSL configuration**:
   Use Mozilla's SSL Configuration Generator for the most secure settings:
   https://ssl-config.mozilla.org/

3. **Set up Content Security Policy**:
   Add to your Nginx configuration:

   ```
   add_header Content-Security-Policy "default-src 'self'; script-src 'self'";
   ```

## Updating the Flask Application

Your Flask application should detect HTTPS connections correctly since we're using the X-Forwarded-Proto header in Nginx.

If you need to specifically handle HTTPS in your Flask app, you can check:

```python
is_secure = request.headers.get('X-Forwarded-Proto') == 'https'
```

## Testing the SSL Quality

After setting up HTTPS, test your SSL configuration quality:

1. SSL Labs Test: https://www.ssllabs.com/ssltest/analyze.html?d=prezentacje.soft-synergy.com

2. Security Headers Test: https://securityheaders.com/?q=prezentacje.soft-synergy.com 