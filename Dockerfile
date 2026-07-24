# Use official Python runtime as a parent image
FROM python:3.9-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

# Set work directory
WORKDIR /

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    default-mysql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt /
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# Copy project code
COPY . /

# Create a startup script
RUN echo '#!/bin/bash\n\
echo "Waiting for MySQL to be ready..."\n\
while ! mysql -h"$MYSQL_HOST" -u"$MYSQL_USER" -p"$MYSQL_PASSWORD" -e "SELECT 1" > /dev/null 2>&1; do\n\
  sleep 2\n\
done\n\
echo "MySQL is ready!"\n\
\n\
echo "Importing backup.sql..."\n\
if [ -f /app/backup.sql ]; then\n\
  mysql -h"$MYSQL_HOST" -u"$MYSQL_USER" -p"$MYSQL_PASSWORD" kai < /app/backup.sql\n\
  echo "Database imported successfully!"\n\
else\n\
  echo "backup.sql not found"\n\
fi\n\
\n\
echo "Starting Flask application..."\n\
exec python app.py' > /entrypoint.sh && \
chmod +x /entrypoint.sh

# Expose port for Flask application
EXPOSE 5000

# Run entrypoint script
ENTRYPOINT ["/entrypoint.sh"]
