# Use the official Python 3.11 slim image as the base image
FROM python:3.11-slim

# Set the working directory
WORKDIR /app

# Create a non-root user
RUN useradd -m dockaiuser

# Switch to the non-root user
USER dockaiuser

# Add user's local bin to PATH for pip-installed scripts
ENV PATH="/home/dockaiuser/.local/bin:${PATH}"

# Copy the pyproject.toml if available
COPY --chown=dockaiuser:dockaiuser pyproject.toml ./

# Copy the requirements file
COPY --chown=dockaiuser:dockaiuser requirements.txt .

# Install dependencies without cache
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire application source code (consider using a .dockerignore to exclude sensitive files)
COPY --chown=dockaiuser:dockaiuser . .

# Install the application as a package
RUN pip install --no-cache-dir .

# Set the entry point for the application
ENTRYPOINT ["dockai", "--help"]