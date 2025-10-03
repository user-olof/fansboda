#!/bin/bash

# Create necessary directories
mkdir -p certificates
mkdir -p certbot-webroot

# Set proper permissions
chmod 755 certificates
chmod 755 certbot-webroot

# Create initial nginx config for ACME challenge
cat > nginx-acme.conf << 'EOF'
events {
    worker_connections 1024;
}

http {
    include       /etc/nginx/mime.types;
    default_type  application/octet-stream;
    
    server {
        listen 80;
        server_name fansboda.dpdns.org;
        
        location /.well-known/acme-challenge/ {
            root /var/www/certbot;
        }
        
        location / {
            return 200 'OK';
            add_header Content-Type text/plain;
        }
    }
}
EOF

echo "Setup complete! Now run:"
echo "1. docker-compose -f docker-compose.yml -f docker-compose.production.yml up -d nginx"
echo "2. docker-compose -f docker-compose.yml -f docker-compose.production.yml run --rm certbot"
echo "3. Replace nginx.conf with the updated version"
echo "4. docker-compose -f docker-compose.yml -f docker-compose.production.yml restart nginx"