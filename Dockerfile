FROM python:3.11-slim

# Install dependencies including ffmpeg
RUN apt-get update && apt-get install -y \
    curl \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY app.py .
COPY record.sh .
COPY channels.json .
COPY templates/ templates/

# Make record.sh executable
RUN chmod +x record.sh

# Create cache directory
RUN mkdir -p /tmp

# Expose port
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:5000/ || exit 1

# Run the application
CMD ["python", "app.py"]
