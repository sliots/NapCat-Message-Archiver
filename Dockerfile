# Dockerfile
FROM python:3.9-slim as builder

WORKDIR /app

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc python3-dev && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

FROM python:3.9-slim
WORKDIR /app

# Copy installed Python packages
COPY --from=builder /root/.local /root/.local
# Make sure scripts in .local are usable
ENV PATH=/root/.local/bin:$PATH

# Copy application files
COPY . .

CMD ["python", "app.py"]
