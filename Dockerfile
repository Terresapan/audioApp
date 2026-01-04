FROM python:3.12-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY web_server.py .
COPY static/ ./static/

# Expose port
EXPOSE 5050

# Run server
CMD ["python", "web_server.py"]
