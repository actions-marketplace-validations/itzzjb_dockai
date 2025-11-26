# Use the official Python 3.11 slim image as the base image
FROM python:3.11-slim

# Set the working directory
WORKDIR /app

# Create a non-root user and switch to it
RUN useradd -m dockai
USER dockai

# Copy the requirements files and the application source code
COPY requirements.txt .
COPY pyproject.toml .
COPY src/ ./src/
COPY tests/ ./tests/
COPY .dockai .
COPY README.md .

# Install the application dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Set the entry point for the application
ENTRYPOINT ["python", "-m", "src.dockai.main", "--help"]

# The application does not expose any ports or health checks as it is a CLI tool.