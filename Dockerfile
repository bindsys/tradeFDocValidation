# Use Python 3.9 slim image as base
FROM python:3.9-slim

# Set working directory in container
WORKDIR /app

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY server.py .
COPY swagger.yaml .
COPY prompts/ ./prompts/

# Create uploads directory
RUN mkdir -p uploads

# Expose port 4000
EXPOSE 4000

# Command to run the application
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "4000"]
