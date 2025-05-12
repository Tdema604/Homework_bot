# Use a pre-built image with ffmpeg already included
FROM jrottenberg/ffmpeg:4.3-ubuntu

# Install Python and pip
RUN apt-get update && apt-get install -y python3 python3-pip

# Set environment variables
ENV PYTHONUNBUFFERED 1

# Set the working directory
WORKDIR /app

# Copy the requirements.txt first
COPY requirements.txt /app/

# Install Python dependencies
RUN pip3 install --no-cache-dir -r requirements.txt

# Copy the rest of the code into the container
COPY . /app/

# Set the command to run the bot
CMD ["python3", "main.py"]
