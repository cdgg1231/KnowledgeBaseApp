#!/bin/bash

echo "Updating package lists..."
apt-get update && apt-get install -y curl gnupg2 unixodbc-dev

echo "Adding Microsoft SQL Server repository..."
curl https://packages.microsoft.com/keys/microsoft.asc | tee /etc/apt/trusted.gpg.d/microsoft.asc
add-apt-repository "$(curl -s https://packages.microsoft.com/config/ubuntu/20.04/prod.list)"

echo "Installing ODBC Driver for SQL Server..."
apt-get update && apt-get install -y msodbcsql18

echo "Installation complete!"
