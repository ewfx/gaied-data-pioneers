import os
import re
import json
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from pydantic import BaseModel, Field
from typing import List, Dict, Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Define Pydantic models matching your exact output structure
class Attachment(BaseModel):
    filename: str
    description: str

class Keywords(BaseModel):
    request_type_keywords: Dict[str, str]
    sub_request_type_keywords: Dict[str, str] = Field(default_factory=dict)
    not_relevant_keywords: Dict[str, str]

class Confidence(BaseModel):
    request_type_confidence: int
    sub_request_type_confidence: int
    assignment_confidence: int

class RequestDetail(BaseModel):
    intent: str
    request_type: str
    sub_request_type: str
    customer_name: str
    email_address: str
    account_user_id: str
    urgency: str
    detailed_description: str
    impact: str
    steps_taken: str
    attachments: List[Attachment]
    keywords: Keywords
    suggested_assignee: str
    assignment_justification: str
    confidence: Confidence

class EmailResponse(BaseModel):
    main_intent: str
    request_details: List[RequestDetail]

class EmailRequestProcessor:
    def __init__(self, email_data):
        self.email_data = email_data
        self.keywords_map = {
            "Adjustment": ["adjustment", "correction", "modification"],
            "AU Transfer": ["AU transfer", "asset utilization", "fund movement"],
            "Closing Notice": ["closing notice", "reallocation fees", "amendment fees", "reallocation principal"],
            "Commitment Change": ["commitment change", "cashless roll", "decrease", "increase"],
            "Fee Payment": ["fee payment", "ongoing fee", "letter of credit fee"],
            "Money Movement - Inbound": ["inbound payment", "principal received", "interest received"],
            "Money Movement - Outbound": ["outbound payment", "foreign currency", "timebound transfer"]
        }
        
        self.matched_keywords = self.find_keywords(email_data.get("body", ""))
        
        # Initialize Langchain components
        self.llm = ChatGoogleGenerativeAI(
            model=os.getenv("MODEL_NAME"),
            google_api_key=os.getenv("GOOGLE_AI_API_KEY"),
            temperature=0
        )
        self.output_parser = JsonOutputParser(pydantic_model=EmailResponse)

        # Load the custom prompt
        try:
            prompt_file_path = os.getenv("PROMPT_FILE_PATH")
            with open(prompt_file_path, "r") as f:
                self.prompt_template = f.read()
        except FileNotFoundError:
            print(f"FileNotFoundError: {prompt_file_path}")
            script_dir = os.path.dirname(os.path.abspath(__file__))
            prompt_path = os.path.join(script_dir, os.getenv("PROMPT_FILE_PATH"))
            with open(prompt_path, "r") as f:
                self.prompt_template = f.read()

    def find_keywords(self, text):
        """Find keywords in the text."""
        matched_keywords = []
        for category, keywords in self.keywords_map.items():
            for keyword in keywords:
                if re.search(r"\b" + re.escape(keyword) + r"\b", text.lower()):
                    matched_keywords.append(keyword)
                    break
        return matched_keywords

    def process_email(self):
        # Prepare attachments for JSON serialization
        attachments_json = []
        for attachment in self.email_data.get("attachments", []):
            attachments_json.append({
                "filename": attachment.get("name", "N/A"),
                "content": attachment.get("content", "N/A")
            })

        prompt = ChatPromptTemplate.from_messages([
            ("system", self.prompt_template),
            ("human", "Subject: {email_subject}\nFrom: {email_sender}\nBody: {email_body}\nAttachments: {email_attachments_json}\nDetected Keywords: {keywords}")
        ])


        # Create the chain
        chain = prompt | self.llm | self.output_parser

        try:
            # Invoke the chain
            chain = prompt | self.llm | self.output_parser
            result = chain.invoke({
                "email_subject": self.email_data.get("subject", "N/A"),
                "email_sender": self.email_data.get("sender", "N/A"),
                "email_body": self.email_data.get("body", ""),
                "email_attachments_json": json.dumps(attachments_json),
                "keywords": ", ".join(self.matched_keywords) if self.matched_keywords else "None"                
            })
            
            return result

        except Exception as e:
            print(f"Error processing email: {e}")
            # Return a default response matching the structure
            return EmailResponse(
                main_intent="ERROR",
                request_details=[
                    RequestDetail(
                        intent="N/A",
                        request_type="N/A",
                        sub_request_type="N/A",
                        customer_name="N/A",
                        email_address="N/A",
                        account_user_id="unavailable",
                        urgency="unavailable",
                        detailed_description="Error processing email",
                        impact="unavailable",
                        steps_taken="N/A",
                        attachments=[],
                        keywords=Keywords(
                            request_type_keywords={},
                            sub_request_type_keywords={},
                            not_relevant_keywords={}
                        ),
                        suggested_assignee="N/A",
                        assignment_justification="Error occurred during processing",
                        confidence=Confidence(
                            request_type_confidence=0,
                            sub_request_type_confidence=0,
                            assignment_confidence=0
                        )
                    )
                ]
            ).model_dump()
        
if __name__ == "__main__":
    email_data = {
        "subject": "Travel Insurance Claim - Delayed Baggage",
        "sender": "robert.chen@example.com",
        "recipients": ["claims.department@example.com"],
        "body": "Hello Claims Team, I need to file a claim for my delayed baggage on my flight to Tokyo. Air France flight AF789 arrived on March 20th, but my luggage was delayed for 48 hours. I had to purchase essential items during this period.",
        "attachments": [
            {
                "name": "Baggage_Delay_Report.pdf",
                "content": "Flight AF789, Delay Report Date: March 20, 2024, Passenger: Robert Chen, Bag Tag: AF456789"
            }
        ]
    }   
    processor = EmailRequestProcessor(email_data)
    result = processor.process_email()
    print(result)

