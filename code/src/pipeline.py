from fetch_emails_process import fetch_last_emails
from langchain_utils import store_email_from_json
from parse_intent import EmailRequestProcessor
def main():
    emails = fetch_last_emails(n=10)
    for i, email_data in enumerate(emails):
        # print the email data , type of email_data
        # print(type(email_data), email_data)
        processor = EmailRequestProcessor(email_data)
        result_json = processor.process_email()
        # print the result_json , type of result_json
        # print(type(result_json), result_json)
        store_email_from_json(email_data, result_json)
if __name__ == "__main__":
    main()


