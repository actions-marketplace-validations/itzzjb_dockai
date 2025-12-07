# Use the official Python 3.11 image as the base image
FROM python:3.11

# Set the working directory
WORKDIR /app

# Install Hadolint for Dockerfile linting (as root before switching user)
RUN wget -qO /usr/local/bin/hadolint https://github.com/hadolint/hadolint/releases/download/v2.12.0/hadolint-Linux-x86_64 && \
    chmod +x /usr/local/bin/hadolint

# Create a non-root user and switch to it
RUN useradd -m dockai
USER dockai

# Copy the necessary files for installation
COPY requirements.txt .
COPY pyproject.toml .
COPY src/ ./src/
COPY README.md .

# Install the application dependencies and the package itself
RUN pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir .

# Ensure the PATH includes the directory where Python scripts are installed
ENV PATH="/home/dockai/.local/bin:$PATH"

# Set the entry point for the application
ENTRYPOINT ["dockai", "--help"]