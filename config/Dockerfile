# Dockerfile
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Copy files
COPY ./app /app
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose FastAPI
EXPOSE 8000

# Start app with Uvicorn
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
