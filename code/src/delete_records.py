"""
Script to delete all records from MongoDB.
WARNING: This is a destructive operation that will permanently delete all data.
"""

import os
import time
from mongo_client import MongoDBClient

def confirm_deletion() -> bool:
    """
    Ask for user confirmation before deletion.
    Returns:
        bool: True if user confirms, False otherwise
    """
    print("\n" + "!"*80)
    print("WARNING: You are about to delete ALL records from the database!")
    print("This operation cannot be undone!")
    print("!"*80 + "\n")
    
    # First confirmation
    confirmation1 = input("Type 'DELETE' (in all caps) to confirm deletion: ")
    if confirmation1 != "DELETE":
        return False
    
    # Second confirmation with 5 second countdown
    print("\nAre you absolutely sure? Countdown starting...")
    for i in range(5, 0, -1):
        print(f"Proceeding with deletion in {i} seconds... Press Ctrl+C to cancel")
        time.sleep(1)
    
    confirmation2 = input("\nType 'YES I AM SURE' (in all caps) to proceed with deletion: ")
    return confirmation2 == "YES I AM SURE"

def delete_all_records():
    """
    Delete all records from MongoDB after confirmation.
    """
    # Initialize MongoDB client
    mongo_client = MongoDBClient()
    
    try:
        # Connect to MongoDB
        if not mongo_client.connect():
            print("Failed to connect to MongoDB. Aborting deletion.")
            return
        
        # Get client and database
        client = mongo_client.get_client()
        db = client['email-triage']  # Use your database name
        
        # Get all collections
        collections = db.list_collection_names()
        
        if not collections:
            print("No collections found in the database.")
            return
        
        # Show collections that will be affected
        print("\nCollections that will be cleared:")
        for collection in collections:
            count = db[collection].count_documents({})
            print(f"- {collection}: {count} documents")
        
        # Get user confirmation
        if not confirm_deletion():
            print("\nDeletion cancelled by user.")
            return
        
        # Proceed with deletion
        print("\nProceeding with deletion...")
        
        total_deleted = 0
        for collection in collections:
            result = db[collection].delete_many({})
            total_deleted += result.deleted_count
            print(f"Deleted {result.deleted_count} documents from {collection}")
        
        print(f"\nOperation complete. Total documents deleted: {total_deleted}")
        
    except Exception as e:
        print(f"An error occurred: {str(e)}")
    
    finally:
        # Always close the connection
        mongo_client.close()

if __name__ == "__main__":
    delete_all_records() 