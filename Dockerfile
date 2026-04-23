FROM python:3.9-slim

WORKDIR /app

# Install necessary libraries
RUN pip install --no-cache-dir telethon python-dotenv

# Copy your code and session files into the container
COPY . .

# Start the bot
CMD ["python", "send.py"]
