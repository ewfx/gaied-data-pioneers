from cmd import PROMPT
from fileinput import filename
import imaplib
import email
import os
import io
import time
from datetime import datetime
import google.generativeai as genai
from extraction_utils import extract_text_from_pdf, extract_text_from_html, perform_ocr
from dotenv import load_dotenv, find_dotenv
from parse_intent import EmailRequestProcessor
from langchain_utils import prepare_email_from_json, email_pipeline
# Find and load the .env file
env_path = find_dotenv()
print(f"Found .env file at: {env_path}")

if not env_path:
    raise Exception(".env file not found!")

# Load environment variables
load_dotenv(env_path, override=True)  # override=True ensures .env values take precedence

# Print debug information
print(f"Current working directory: {os.getcwd()}")
print(f"Environment variable before loading: {os.environ.get('EMAIL_USER', 'Not set')}")
print(f"Loaded EMAIL_USER from .env: {os.getenv('EMAIL_USER')}")

# Email Credentials
EMAIL_USER = os.getenv("EMAIL_USER")
if not EMAIL_USER:
    raise Exception("EMAIL_USER environment variable not set!")

EMAIL_PASS = os.getenv("EMAIL_PASS")
if not EMAIL_PASS:
    raise Exception("EMAIL_PASS environment variable not set!")

print(f"Using EMAIL_USER: {EMAIL_USER}")

IMAP_SERVER = "imap.gmail.com"
MAILBOX = "INBOX"
POLL_INTERVAL = 10  # seconds

class EmailMonitor:
    def __init__(self):
        self.mail = None
        self.processed_ids = set()
        self.last_refresh_time = time.time()
        self.REFRESH_INTERVAL = 60  # Refresh connection every 60 seconds
        self.connect()
        
    def connect(self):
        """Establish IMAP connection"""
        if self.mail:
            try:
                self.mail.close()
                self.mail.logout()
            except:
                pass
                
        self.mail = imaplib.IMAP4_SSL(IMAP_SERVER)
        self.mail.login(EMAIL_USER, EMAIL_PASS)
        self.refresh_mailbox()
        print("Connected to IMAP server")
        
    def refresh_mailbox(self):
        """Refresh the mailbox state"""
        try:
            self.mail.select(MAILBOX)  # Re-select the mailbox to refresh
            self.last_refresh_time = time.time()
            print("Mailbox refreshed")
        except Exception as e:
            print(f"Error refreshing mailbox: {str(e)}")
            self.connect()  # Reconnect if refresh fails

    def process_email(self, email_id):
        """Process a single email"""
        try:
            print(f"Fetching email content for ID: {email_id}")
            _, msg_data = self.mail.fetch(email_id, "(RFC822)")
            
            if not msg_data or not msg_data[0]:
                raise Exception("No message data received")
            
            if isinstance(msg_data[0][1], dict):
                print("Received unexpected dictionary instead of email data")
                return None
                
            raw_email = msg_data[0][1]
            if not isinstance(raw_email, bytes):
                print(f"Unexpected data type for raw_email: {type(raw_email)}")
                raw_email = str(raw_email).encode()
                
            msg = email.message_from_bytes(raw_email)

            subject = msg.get("Subject", "N/A")
            sender = msg.get("From", "N/A")
            date = email.utils.parsedate_to_datetime(msg.get("Date"))
            
            print(f"Processing email: {subject}")
            
            body = ""
            attachments = []

            if msg.is_multipart():
                for part in msg.walk():
                    content_type = part.get_content_type()
                    filename = part.get_filename()

                    if content_type == "text/plain":
                        body = part.get_payload(decode=True).decode(errors="ignore")
                    elif content_type == "text/html":
                        html_content = part.get_payload(decode=True).decode(errors="ignore")
                        body = extract_text_from_html(html_content)
                    elif filename and filename.lower().endswith(".pdf"):
                        print(f"Processing PDF attachment: {filename}")
                        file_data = part.get_payload(decode=True)
                        extracted_text = extract_text_from_pdf(file_data)
                        attachments.append({"name": filename, "content": extracted_text})
                    elif filename and any(filename.lower().endswith(ext) for ext in [".png", ".jpg", ".jpeg"]):
                        file_data = part.get_payload(decode=True)
                        image_io = io.BytesIO(file_data)
                        ocr_text = perform_ocr(image_io)
                        if ocr_text.strip():
                            attachments.append({"name": filename, "content": ocr_text})
            else:
                body = msg.get_payload(decode=True).decode(errors="ignore")

            # Only mark as seen after successful processing
            print(f"Marking email {email_id} as seen")
            self.mail.store(email_id, '+FLAGS', '\\Seen')
            
            return {
                "subject": subject,
                "sender": sender,
                "date": date.isoformat(),
                "body": body.strip(),
                "attachments": attachments
            }
        except Exception as e:
            print(f"Error processing email {email_id}: {str(e)}")
            return None

    def fetch_unseen_emails(self):
        """Fetch all unseen emails"""
        try:
            # Check if we need to refresh the connection
            current_time = time.time()
            if current_time - self.last_refresh_time > self.REFRESH_INTERVAL:
                print("Refreshing connection...")
                self.refresh_mailbox()
            
            # Check connection with noop
            try:
                self.mail.noop()
            except:
                print("Connection lost, reconnecting...")
                self.connect()
            
            print("\nFetching unseen emails...")
            _, messages = self.mail.search(None, 'UNSEEN')
            email_ids = messages[0].split()
            
            print(f"Found {len(email_ids)} unseen emails")
            
            if not email_ids:
                return []

            emails = []
            for email_id in email_ids:
                try:
                    if email_id not in self.processed_ids:
                        print(f"Processing email ID: {email_id}")
                        email_data = self.process_email(email_id)
                        if email_data:  # Only add if processing was successful
                            emails.append(email_data)
                            self.processed_ids.add(email_id)
                            print(f"Successfully processed email: {email_data['subject']}")
                        else:
                            print(f"Failed to process email ID: {email_id}")
                    else:
                        print(f"Email ID {email_id} already processed, skipping...")
                except Exception as e:
                    print(f"Error processing email {email_id}: {str(e)}")
                    continue

            return emails
            
        except Exception as e:
            print(f"Error in fetch_unseen_emails: {str(e)}")
            # Try to reconnect
            self.connect()
            return []

    def monitor_emails(self):
        """Continuously monitor for new emails"""
        while True:
            try:
                new_emails = self.fetch_unseen_emails()
                if new_emails:
                    yield new_emails
                time.sleep(POLL_INTERVAL)
            except Exception as e:
                print(f"Error in monitor_emails: {str(e)}")
                self.connect()  # Reconnect on error
                time.sleep(POLL_INTERVAL)
import json
if __name__ == "__main__":
    monitor = EmailMonitor()
    print(f"Starting email monitoring for {EMAIL_USER}...")
    
    for emails in monitor.monitor_emails():
        for m in emails:
            # Process the email as needed
            processor = EmailRequestProcessor(m)
            result = processor.process_email()
            # format the logging to be more readable
    

            final_email_doc = prepare_email_from_json(m, result)
            final_email_doc = email_pipeline(final_email_doc)
            
            