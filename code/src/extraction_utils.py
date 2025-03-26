from bs4 import BeautifulSoup
import fitz  # PyMuPDF
from google.cloud import vision
import json
import os
import io

def perform_ocr(image_bytes_io):
    try:
        credentials_path = os.getenv("CREDENTIALS_PATH")
        if not os.path.exists(credentials_path):
            raise FileNotFoundError("cloud-vision-api-key.json not found in project directory.")

        # Check if file content is valid JSON
        with open(credentials_path, "r") as f:
            try:
                json.load(f)
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSON in credentials file: {e}")

        client = vision.ImageAnnotatorClient.from_service_account_file(credentials_path)

        image_bytes_io.seek(0)
        content = image_bytes_io.read()
        image = vision.Image(content=content)

        response = client.text_detection(image=image)

        if response.error.message:
            raise Exception(f"Vision API Error: {response.error.message}")

        if response.text_annotations:
            return response.text_annotations[0].description
        else:
            return "No text found in image."

    except Exception as e:
        print(f"OCR Error: {e}")
        return f"OCR failed: {e}"

def extract_text_from_pdf(file_data):
    extracted_text = ""
    try:
        with io.BytesIO(file_data) as pdf_buffer:
            doc = fitz.open(stream=pdf_buffer, filetype="pdf")
            extracted_text = "\n".join([page.get_text("text") for page in doc])
    except Exception as e:
        print(f"PDF Parsing Error: {e}")
    return extracted_text.strip()

def extract_text_from_html(html_content):
    soup = BeautifulSoup(html_content, "html.parser")
    return soup.get_text(separator="\n").strip()