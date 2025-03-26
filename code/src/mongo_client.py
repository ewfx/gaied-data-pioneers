"""
MongoDB client configuration and connection handler.
This module provides functionality to connect to MongoDB Atlas using environment variables
for secure credential management.
"""

import os
from typing import Optional
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class MongoDBClient:
    def __init__(self):
        """Initialize MongoDB client with credentials from environment variables."""
        self.username = os.getenv('MONGODB_USERNAME')
        self.password = os.getenv('MONGODB_PASSWORD')
        self.uri = f"mongodb+srv://{self.username}:{self.password}@data-pioneers.76ugf.mongodb.net/?appName=data-pioneers"
        self.client: Optional[MongoClient] = None

    def connect(self) -> bool:
        """
        Establish connection to MongoDB Atlas.
        
        Returns:
            bool: True if connection is successful, False otherwise
        """
        try:
            if not self.username or not self.password:
                raise ValueError("MongoDB credentials not found in environment variables")

            self.client = MongoClient(self.uri, server_api=ServerApi('1'))
            # Send a ping to confirm a successful connection
            self.client.admin.command('ping')
            print("Successfully connected to MongoDB Atlas!")
            return True
        except Exception as e:
            print(f"Failed to connect to MongoDB: {str(e)}")
            return False

    def get_client(self) -> Optional[MongoClient]:
        """
        Get the MongoDB client instance.
        
        Returns:
            Optional[MongoClient]: MongoDB client instance if connected, None otherwise
        """
        return self.client

    def close(self):
        """Close the MongoDB connection if it exists."""
        if self.client:
            self.client.close()
            print("MongoDB connection closed.")

# Example usage
if __name__ == "__main__":
    mongo_client = MongoDBClient()
    if mongo_client.connect():
        # Use the client for operations
        client = mongo_client.get_client()
        # ... perform operations ...
        mongo_client.close() 