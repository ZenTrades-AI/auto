# Use the official Playwright Docker image directly from Microsoft!
# This image contains every single Linux OS dependency, graphics driver, and pre-installed browser automatically.
FROM mcr.microsoft.com/playwright/python:v1.40.0-jammy

# Set the working directory on the server
WORKDIR /app

# Copy your requirements file
COPY requirements.txt .

# Install the Python packages
RUN pip install --no-cache-dir -r requirements.txt

# Copy all your scripts and code into the container
COPY . .

# Force Python to print logs immediately to the Render Dashboard without buffering
ENV PYTHONUNBUFFERED=1

# Expose the standard Render port
EXPOSE 10000

# Start Gunicorn with threaded workers to securely handle the background UI threads!
CMD ["gunicorn", "app:flask_app", "--bind", "0.0.0.0:10000", "--workers", "1", "--threads", "4", "--timeout", "100"]
