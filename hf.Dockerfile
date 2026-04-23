# Pull your private image from Docker Hub
FROM hoopstreet/tg-message-sender:v1.0.8

# The environment variables are already in the image or 
# can be set in HF Space Secrets.
CMD ["python", "send.py"]
