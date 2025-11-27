#!/bin/bash

# Setup script for QtEmail backend
# Run this after starting Docker services

echo "==================================="
echo "QtEmail Backend Setup"
echo "==================================="

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install dependencies
echo "Installing Python dependencies..."
pip install -r requirements.txt

# Wait for database to be ready
echo "Waiting for database..."
sleep 5

# Run migrations
echo "Running database migrations..."
python manage.py makemigrations
python manage.py migrate

# Create superuser (optional)
echo ""
echo "Would you like to create a superuser? (yes/no)"
read -r response
if [[ "$response" == "yes" ]]; then
    python manage.py createsuperuser
fi

echo ""
echo "==================================="
echo "Setup complete!"
echo "==================================="
echo ""
echo "To start the development server:"
echo "  python manage.py runserver"
echo ""
echo "To start Celery worker:"
echo "  celery -A qutemail worker -l info"
echo ""
echo "To start Celery beat:"
echo "  celery -A qutemail beat -l info"
echo ""
echo "Or use Docker:"
echo "  docker compose up --build"
