import pyodbc
import os
from dotenv import load_dotenv

# Load .env variables
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

try:
    print("Attempting to connect to Azure SQL Database...")
    conn = pyodbc.connect(DATABASE_URL, timeout=30)
    print("✅ Database connection successful!")
    conn.close()
except pyodbc.Error as e:
    print(f"❌ Database connection failed: {e}")
