#!/usr/bin/env bash
# exit on error
set -o errexit

# Install system dependencies required by the application
apt-get update
apt-get install -y tesseract-ocr libgl1-mesa-glx libsm6 libxext6 poppler-utils

# Install Python dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Run Django migrations and collectstatic
python manage.py collectstatic --no-input
python manage.py migrate 