# Stage 1: Build
FROM python:3.9.17-slim AS build

# Set the working directory
WORKDIR /app

# Copy the requirements file and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create a non-root user and switch to it
RUN useradd -m appuser
USER appuser

# Copy the entire application source code
COPY . .

# Stage 2: Runtime
FROM python:3.9.17-slim

# Set the working directory
WORKDIR /app

# Copy the application files and installed dependencies from the build stage
COPY --from=build /app /app

# Create a non-root user and switch to it
RUN useradd -m appuser
USER appuser

# Expose the port the app runs on
EXPOSE 5000

# Command to run the application
CMD ["python", "app.py"]