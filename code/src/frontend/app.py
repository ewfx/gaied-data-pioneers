"""
Main Streamlit application for the email processing system.
"""
import streamlit as st
import sys
import os
import requests
# Add the parent directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def main():
    st.set_page_config(
        page_title="Email Processing System",
        page_icon="📧",
        layout="wide"
    )

    st.title("📩 AI-Powered Email Processor")

    # ✅ FastAPI Backend URL
    API_URL = "http://127.0.0.1:8000/fetch_emails/"

    if st.button("🔍 Fetch & Analyze Latest Email"):
        with st.spinner("Fetching emails..."):
            try:
                response = requests.get(API_URL)
                if response.status_code == 200:
                    data = response.json()
                    if data["emails"]:
                        for i, email_data in enumerate(data["emails"]):
                            st.subheader(f"📧 Email {i+1}")
                            st.json(email_data)
                            st.markdown("---")
                    else:
                        st.warning("No emails found.")
                else:
                    st.error("Error fetching emails. Try again.")
            except Exception as e:
                st.error(f"Error: {e}")

if __name__ == "__main__":
    main() 