#!/bin/bash

# Bootstrap Mail Server Script
# Sets up a development mail server for testing

echo "==================================="
echo "QtEmail Mail Server Bootstrap"
echo "==================================="

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "Error: Docker is not installed"
    exit 1
fi

echo "Starting mail server container..."

# Start MailHog for development testing
docker run -d \
  --name qutemail_mailserver \
  -p 1025:1025 \
  -p 8025:8025 \
  mailhog/mailhog

if [ $? -eq 0 ]; then
    echo "✓ Mail server started successfully"
    echo ""
    echo "SMTP Server: localhost:1025"
    echo "Web UI: http://localhost:8025"
    echo ""
    echo "Update your .env file with:"
    echo "SMTP_HOST=localhost"
    echo "SMTP_PORT=1025"
    echo "SMTP_USE_TLS=False"
else
    echo "✗ Failed to start mail server"
    exit 1
fi
