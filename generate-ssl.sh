#!/bin/bash

# Generate SSL certificates for development
echo "Generating SSL certificates for development..."

# Create SSL directory
mkdir -p nginx/ssl

# Generate self-signed certificate for nginx
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout nginx/ssl/key.pem \
    -out nginx/ssl/cert.pem \
    -subj "/C=US/ST=State/L=City/O=Organization/CN=localhost"

# Generate certificates for each service
for service in backend agents/cybersecurity agents/devops; do
    echo "Generating certificate for $service..."
    openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
        -keyout $service/key.pem \
        -out $service/cert.pem \
        -subj "/C=US/ST=State/L=City/O=Organization/CN=localhost"
done

echo "SSL certificates generated successfully!"
