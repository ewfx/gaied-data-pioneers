"""
Module for generating and managing email embeddings using all-MiniLM-L6-v2 from Hugging Face.
"""

from typing import Dict, Any, List
from sentence_transformers import SentenceTransformer
import torch

class EmailEmbeddingGenerator:
    def __init__(self):
        """Initialize the Jina embeddings model."""
        self.model = SentenceTransformer("all-MiniLM-L6-v2")
        self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        self.model.to(self.device)

    def generate_email_text(self, 
                          subject: str, 
                          sender: str, 
                          recipients: List[str], 
                          body: str, 
                          attachments: List[Dict[str, str]]) -> str:
        """
        Generate formatted email text for embedding.
        
        Args:
            subject (str): Email subject
            sender (str): Email sender
            recipients (List[str]): List of recipients
            body (str): Email body
            attachments (List[Dict[str, str]]): List of attachments
            
        Returns:
            str: Formatted email text
        """
        attachment_text = "\n".join([
            f"- {att['name']}: {att['content']}"
            for att in attachments
        ])
        
        email_text = f"""
Subject: {subject}
From: {sender}
To: {', '.join(recipients)}
Body: {body}
Attachments: {attachment_text}
"""
        return email_text.strip()

    def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for the given text using Jina's model.
        
        Args:
            text (str): Text to generate embedding for
            
        Returns:
            List[float]: Embedding vector
        """
        try:
            # Generate embedding
            embedding = self.model.encode(
                text,
                convert_to_tensor=True,
                device=self.device
            )
            
            # Convert to list and move to CPU if needed
            return embedding.cpu().tolist()
            
        except Exception as e:
            print(f"Error generating embedding: {str(e)}")
            raise

    def get_embedding_data(self,
                          subject: str,
                          sender: str,
                          recipients: List[str],
                          body: str,
                          attachments: List[Dict[str, str]]) -> Dict[str, Any]:
        """
        Generate embedding and metadata for email content.
        
        Args:
            subject (str): Email subject
            sender (str): Email sender
            recipients (List[str]): List of recipients
            body (str): Email body
            attachments (List[Dict[str, str]]): List of attachments
            
        Returns:
            Dict[str, Any]: Dictionary containing embedding and metadata
        """
        try:
            # Generate formatted email text
            email_text = self.generate_email_text(
                subject=subject,
                sender=sender,
                recipients=recipients,
                body=body,
                attachments=attachments
            )
            
            # Generate embedding
            embedding = self.generate_embedding(email_text)
            
            # Prepare embedding data
            return {
                "embedding": embedding,
                "embedding_model": "all-MiniLM-L6-v2",
                "embedding_metadata": {
                    "text_length": len(email_text),
                    "has_attachments": len(attachments) > 0,
                    "num_recipients": len(recipients),
                    "device_used": self.device
                }
            }
            
        except Exception as e:
            print(f"Warning: Failed to generate embedding: {str(e)}")
            return None 
        
from sentence_transformers import SentenceTransformer

if __name__ == "__main__":
    
    sentence = "What is the weather like in Berlin today?"
    embedding = EmailEmbeddingGenerator().generate_embedding(sentence)
    print(embedding)
