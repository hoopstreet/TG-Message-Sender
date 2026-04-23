FROM python:3.9-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy everything (including your .session files)
COPY . .

# Run the manager bot
CMD ["python", "send.py"]
