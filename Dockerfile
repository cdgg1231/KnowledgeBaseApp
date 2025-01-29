# Use the official Python 3.11 image
FROM python:3.11

# Install ODBC Driver for SQL Server
RUN apt-get update && apt-get install -y curl gnupg2 unixodbc-dev && \
    curl https://packages.microsoft.com/keys/microsoft.asc | tee /etc/apt/trusted.gpg.d/microsoft.asc && \
    add-apt-repository "$(curl -s https://packages.microsoft.com/config/ubuntu/20.04/prod.list)" && \
    apt-get update && apt-get install -y msodbcsql18

# Set the working directory
WORKDIR /app

# Copy only necessary files to reduce image size
COPY app.py requirements.txt /app/
COPY templates /app/templates
COPY static /app/static  # This ensures all PDFs and documents are copied
COPY .env /app/.env  # Copy environment variables if required

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Ensure the static folder exists with proper permissions
RUN mkdir -p /app/static/documents && chmod -R 755 /app/static

# Expose port for Render (update if using 5000 instead)
EXPOSE 10000

# Run the Flask app with Gunicorn
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:10000", "app:app"]
