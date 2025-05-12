# Use a pre-built Python image
FROM python:3.9-slim

# Install ffmpeg from the official jrottenberg/ffmpeg image that has it pre-installed
RUN apt-get update && apt-get install -y \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory inside the container
WORKDIR /app

# Copy the requirements file and install dependencies
COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of your project files to the container
COPY . .

# Expose the port if needed
EXPOSE 5000

# Command to run your bot
CMD ["python3", "main.py"]
