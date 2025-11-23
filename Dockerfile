FROM python:3.11-slim

# Install git (optional, but often useful for scanners)
RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

# Copy the tool's source code into the container
WORKDIR /app
COPY . /app

# Install the tool
RUN pip install --no-cache-dir .

# Set the working directory to where GitHub mounts the user's code
WORKDIR /github/workspace

# Set the entrypoint to your CLI tool
ENTRYPOINT ["dockai"]
