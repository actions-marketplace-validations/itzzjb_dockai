FROM python:3.11-slim

# Install git and prerequisites for Docker CLI
RUN apt-get update && apt-get install -y \
    git \
    ca-certificates \
    curl \
    gnupg \
    && install -m 0755 -d /etc/apt/keyrings \
    && curl -fsSL https://download.docker.com/linux/debian/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg \
    && chmod a+r /etc/apt/keyrings/docker.gpg \
    && echo \
    "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/debian \
    $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null \
    && apt-get update \
    && apt-get install -y docker-ce-cli \
    && rm -rf /var/lib/apt/lists/*

# Copy the tool's source code into the container
WORKDIR /app
COPY . /app

# Install the tool
RUN pip install --no-cache-dir .

# Set the working directory to where GitHub mounts the user's code
WORKDIR /github/workspace

# Set the entrypoint to your CLI tool
ENTRYPOINT ["dockai"]
