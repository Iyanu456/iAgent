import os
import logging
from mongoengine import connect, disconnect
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
DATABASE_NAME = os.getenv("DATABASE_NAME")

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def connect_to_db():
    try:
        connect(db=f"{DATABASE_NAME}", host=f"{DATABASE_URL}")
        logging.info("Database connection successful!")
    except Exception as e:
        logging.error(f"Database connection failed: {e}")


def disconnect_db():
    try:
        disconnect()
        logging.info("Database disconnected successfully!")
    except Exception as e:
        logging.error(f"Error while disconnecting: {e}")

