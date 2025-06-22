# Dockerfile

# Start from a specific Python version
FROM python:3.11-slim

# Set environment variables to optimize Python in Docker
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Install system dependencies required for Open Babel
RUN apt-get update && \
    apt-get install -y --no-install-recommends cmake libopenbabel-dev && \
    # Clean up the apt cache to keep the image small
    rm -rf /var/lib/apt/lists/*

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file and install Python packages
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of your application code into the container
COPY . .
# Make port 8080 available to the world outside this container
EXPOSE 8080
# Define environment variable
ENV PORT 8080

# Command to run the application using Gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "app:app"]
