FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# Run the setup script to ensure data exists inside the image if not mounted
RUN python setup_env.py

# Default command (CLI as requested)
ENTRYPOINT ["python", "run_agent_hybrid.py"]