FROM python:3.9-slim

# Set environment to skip interactive prompts
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Step 1: Inject and install dependencies first (for caching)
COPY requirements.txt .
RUN pip install --no-cache-dir --prefer-binary -r requirements.txt

# Step 2: Inject the rest of the source code
COPY . .

# Step 3: Trigger the bot
CMD ["python", "send.py"]
