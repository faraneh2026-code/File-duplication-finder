FROM python:3.12-slim

LABEL maintainer="Prepaire SDK Team"
LABEL description="File Duplication Finder — Identifies identical files in a directory"
LABEL version="1.0.0"

# Set working directory
WORKDIR /app

# Install dependencies
RUN pip install --no-cache-dir PyPDF2 pycryptodome

# Copy application code
COPY find_duplicates.py .


# Create a mount point for user data
VOLUME ["/data"]

# Default entrypoint: run the finder script
ENTRYPOINT ["python", "find_duplicates.py"]

# Default command: scan /data with all-files mode
CMD ["/data", "--all-files"]
