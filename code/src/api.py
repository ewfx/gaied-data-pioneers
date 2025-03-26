from fastapi import FastAPI

from mongo_client import MongoDBClient
from fastapi.responses import JSONResponse
import json
from bson import json_util
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# FastAPI Endpoint to Process Emails
@app.get("/fetch_emails/")
def fetch_and_process_emails():
    """
    Retrieve all records from MongoDB database.
    Returns:
        JSON response containing all email records sorted by created_at in descending order
    """
    try:
        # Initialize MongoDB client
        mongo_client = MongoDBClient()
        
        if mongo_client.connect():
            # Get the database and collection
            db = mongo_client.get_client().get_database('email-triage')
            emails_collection = db.emails
            
            # Fetch all documents, sort by created_at in descending order
            cursor = emails_collection.find({}).sort("created_at", -1)
            all_records = json.loads(json_util.dumps(list(cursor)))
            
            return JSONResponse(content={"records": all_records})
        else:
            return JSONResponse(
                status_code=500,
                content={"error": "Failed to connect to MongoDB"}
            )
            
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": f"Error retrieving records: {str(e)}"}
        )
    finally:
        if mongo_client:
            mongo_client.close()