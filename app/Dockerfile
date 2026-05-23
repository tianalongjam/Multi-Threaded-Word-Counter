FROM python:3.13-slim

# Install system dependencies (needed for pandas, pyarrow, etc.)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    g++ \
    libffi-dev \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
RUN pip install --no-cache-dir pandas matplotlib pyarrow fastparquet

# Set working directory
WORKDIR /app

# Copy all files into container
COPY . /app

# Default command (can be overridden)
CMD ["python3.13", "final.py"]

