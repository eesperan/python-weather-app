# Use the official Python image from the Docker Hub, slim version for smaller size
FROM python:3.9-slim

# Set environment variables for Python
ENV PYTHONUNBUFFERED=1

# Create a non-root user for security purposes
RUN adduser --disabled-password --gecos '' appuser

# Set the working directory
WORKDIR /app

# Run a system update, and clean up the cache
RUN apt-get update && apt-get -y dist-upgrade \
    && rm -rf /var/lib/apt/lists/*

# Copy the requirements file and install dependencies
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . /app/

# Chown the application files to the non-root user
RUN chown -R appuser:appuser /app

# Change to the non-root user
USER appuser

ENTRYPOINT ["python", "/app/weather_app.py"]
