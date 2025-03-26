"""
Script to store email data in MongoDB with classification results and embeddings.
This script handles storing both input email data, its classification results, and embeddings.
"""

from mongo_client import MongoDBClient
from typing import Dict, Any, List
from langchain.schema.runnable import RunnableLambda
from datetime import datetime
from email_embeddings import EmailEmbeddingGenerator
import os

def prepare_email_data(
    subject: str,
    sender: str,
    recipients: List[str],
    body: str,
    attachments: List[Dict[str, str]],
    main_intent: str,
    request_details: List[Dict[str, Any]]
) -> Dict[str, Any]:
   
    mongo_client = MongoDBClient()
    email_doc = {
        "subject": subject,
        "sender": sender,
        "recipients": recipients,
        "body": body,
        "attachments": attachments,
        "main_intent": main_intent,
        "request_details": request_details,
        "created_at": datetime.now(),
        "updated_at": datetime.now()
    }

    return email_doc

def add_embedding_data(email_doc: Dict[str, Any]) -> Dict[str, Any]:
    embedding_generator = EmailEmbeddingGenerator()
    embedding_data = embedding_generator.get_embedding_data(
        subject=email_doc["subject"],
        sender=email_doc["sender"],
        recipients=email_doc["recipients"],
        body=email_doc["body"],
        attachments=email_doc["attachments"]
    )
    # Store only the embedding vector, not the entire embedding data dictionary
    email_doc["embedding"] = embedding_data["embedding"] if embedding_data else None
    return email_doc


def perform_duplicate_check(email_doc: Dict[str, Any]) -> Dict[str, Any]:
    """
    Check if an email with the same embedding already exists in the database.
    """
    mongo_client = MongoDBClient()
    try:
        if mongo_client.connect():
            db = mongo_client.get_client().get_database('email-triage')
            emails_collection = db.emails

            if email_doc["embedding"]:
                # Create search query using the embedding
                search_query = [{
                    "$vectorSearch": {
                        "index": "email_embedding",
                        "path": "embedding",
                        "queryVector": email_doc["embedding"],
                        "numCandidates": 5,  # Number of nearest neighbors to consider
                        "limit": 3  # Return top 3 results
                    }
                }]

                # Add fields to return
                search_query.append({
                    "$project": {
                        "_id": 1,
                        "subject": 1,
                        "sender": 1,
                        "body": 1,
                        "score": {"$meta": "vectorSearchScore"}
                    }
                })

                print("\nPerforming vector search for similar emails...")

                # Execute search
                similar_emails = list(emails_collection.aggregate(search_query))

                #create a dict to return which will be used to update the email_docs
                update_dict = {}
                if similar_emails:
                    for email in similar_emails:
                        # is the score greater than the threshold?
                        if email.get('score') > float(os.getenv('DUPLICATE_CHECK_THRESHOLD')):
                            # update the email_doc with duplicate bool as true and the duplicate email id, score
                            email_doc["duplicate"] = True
                            email_doc["duplicate_email_id"] = email.get('_id')
                            email_doc["duplicate_score"] = email.get('score')

                else:
                    print("No similar emails found")   
                return email_doc
        else:
            print("Failed to connect to MongoDB")
    except Exception as e:
        print(f"Error performing duplicate check: {str(e)}")

def store_email_data(email_doc: Dict[str, Any]) -> Dict[str, Any]:
    mongo_client = MongoDBClient()
    if mongo_client.connect():
        db = mongo_client.get_client().get_database('email-triage')
        emails_collection = db.emails
        emails_collection.insert_one(email_doc)
        return email_doc
    else:
        print("Failed to connect to MongoDB")
        return email_doc
    
def prepare_email_from_json(input_json: Dict[str, Any], output_json: Dict[str, Any]) -> bool:
    """
    Store email data from input and output JSON files.
    
    Args:
        input_json (Dict[str, Any]): Input JSON containing email data
        output_json (Dict[str, Any]): Output JSON containing classification results
        
    Returns:
        bool: True if storage was successful, False otherwise
    """
    try:
        # Extract data from input JSON
        subject = input_json.get("subject", "")
        sender = input_json.get("sender", "")
        recipients = input_json.get("recipients", [])
        body = input_json.get("body", "")
        attachments = input_json.get("attachments", [])
        
        # Extract data from output JSON
        main_intent = output_json.get("main_intent", "")
        request_details = output_json.get("request_details", [])
        
        # prepare the data
        email_doc = prepare_email_data(
            subject=subject,
            sender=sender,
            recipients=recipients,
            body=body,
            attachments=attachments,
            main_intent=main_intent,
            request_details=request_details,
        )
        return email_doc
        
    except Exception as e:
        print(f"Error processing JSON data: {str(e)}")
        return False

def email_pipeline(email_doc: Dict[str, Any]) -> Dict[str, Any]:
    add_embedding_runnable = RunnableLambda(add_embedding_data)
    perform_duplicate_check_runnable = RunnableLambda(perform_duplicate_check)
    store_email_data_runnable = RunnableLambda(store_email_data)

    # Create a LangChain pipeline
    email_pipeline = (
        add_embedding_runnable
        | perform_duplicate_check_runnable
        | store_email_data_runnable
    )

    return email_pipeline.invoke(email_doc)

if __name__ == "__main__":
    input_data = {
        "subject": "Travel Insurance Claim - Delayed Baggage",
        "sender": "robert.chen@example.com",
        "recipients": ["claims.department@example.com"],
        "body": "Hello Claims Team, I need to file a claim for my delayed baggage on my flight to Tokyo. Air France flight AF789 arrived on March 20th, but my luggage was delayed for 48 hours. I had to purchase essential items during this period.",
        "attachments": [
            {
                "name": "Baggage_Delay_Report.pdf",
                "content": "Flight AF789, Delay Report Date: March 20, 2024, Passenger: Robert Chen, Bag Tag: AF456789"
            },
            {
                "name": "Emergency_Purchases.pdf",
                "content": "Store: Tokyo Mall, Date: March 20-21, 2024, Total Amount: ¥25,000, Items: Essential clothing and toiletries"
            }
        ]
    }

    output_data = {
        "main_intent": "Credit Card Inquiry",
        "request_details": [
            {
            "intent": "Credit Card Issue",
            "request_type": "Balance Inquiry",
            "sub_request_type": "Due Date and Rewards",
            "customer_name": "John Doe",
            "email_address": "johndoe@example.com",
            "account_user_id": "JD123456",
            "urgency": "High",
            "detailed_description": "Customer wants to know the current balance, next payment due date, and available reward points for their credit card account.",
            "impact": "Customer needs this information urgently to make a payment.",
            "steps_taken": "Checked online banking but couldn't find the due date.",
            "attachments": [
                {
                "filename": "credit_card_statement.pdf",
                "description": "Latest credit card statement showing transactions."
                }
            ],
            "keywords": {
                "request_type_keywords": {
                "credit card balance": "12345USD",
                "next payment due date": "12/12/2025",
                "rewards points": "123"
                },
                "sub_request_type_keywords": {
                "interest_rate": "15%",
                "minimum payment": "500USD"
                },
                "not_relevant_keywords": {
                "Library Card Number": "12345678",
                "Son's Birthday": "14-Sep-2020",
                "Religion": "mentioned",
                "Coding Skills": "mentioned",
                "Manager Name": "mentioned",
                "Hobby": "mentioned"
                }
            },
            "suggested_assignee": "Credit Card Support Team",
            "assignment_justification": "Request relates to credit card balance and due date, which falls under the Credit Card Support Team's expertise.",
            "confidence": {
                "request_type_confidence": 0.95,
                "sub_request_type_confidence": 0.90,
                "assignment_confidence": 0.92
            }
            }
        ]
        }

    
    # Store the email data
    final_email_doc = prepare_email_from_json(input_data, output_data)
    final_email_doc = email_pipeline(final_email_doc)
    if final_email_doc:
        print("Email data stored successfully")
    else:
        print("Failed to store email data") 