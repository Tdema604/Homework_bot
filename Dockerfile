# Use the official Python base image
FROM python:3.9-slim

# Set environment variables for non-interactive installs
ENV PYTHONUNBUFFERED 1

# Set the working directory in the container
WORKDIR /app

# Copy the requirements.txt first (so Docker caches this layer)
COPY requirements.txt /app/

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of your application code
COPY . /app/

# Set the command to run the bot (main.py)
CMD ["python", "main.py"]
