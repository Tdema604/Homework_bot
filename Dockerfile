# Use the official Python image as the base
FROM python:3.9-slim

# Install dependencies, including ffmpeg
RUN apt-get update && apt-get install -y \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# Copy all files from the local directory to the container
COPY . .

# Expose the port that your app will run on
EXPOSE 5000

# Command to run your app
CMD ["python3", "main.py"]
