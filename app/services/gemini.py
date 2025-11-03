from typing import Optional
import os
import google.generativeai as genai
from app.core.config import settings


class GeminiService:
    """Service for Gemini AI integration"""
    
    def __init__(self):
        self.enabled = False
        self.model = None
        self._initialize()
    
    def _initialize(self):
        """Initialize Gemini API"""
        api_key = settings.GEMINI_API_KEY or os.getenv("GEMINI_API_KEY")
        model_name = settings.GEMINI_MODEL or os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
        
        if not api_key:
            print("⚠️  WARNING: GEMINI_API_KEY not found in environment variables!")
            print("⚠️  Set it in .env file or export GEMINI_API_KEY=your_key")
            print("⚠️  Answers will use basic formatting instead of AI generation")
            self.enabled = False
            return
        
        try:
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel(model_name)
            self.enabled = True
            print(f"✅ Gemini API initialized with model: {model_name}")
        except Exception as e:
            print(f"⚠️  Error initializing Gemini: {str(e)}")
            self.enabled = False
    
    def generate_answer(self, query: str, context: str) -> str:
        """
        Generate answer using Gemini AI
        
        Args:
            query: User's question
            context: Retrieved context from documents
            
        Returns:
            Generated answer text
        """
        if not self.enabled or not self.model:
            return None
        
        try:
            prompt = f"""You are a helpful documentation assistant. Answer the user's question based on the provided context.

Context from documentation:

{context}

User Question: {query}

Instructions:
- FIRST, look for explicit definitions or explanations in the context (especially sections with headings like "What is X?", "Introduction", "Overview", etc.)
- If you find a definition or explanation section, use it as the primary source for your answer
- Provide a clear, accurate answer based on the context
- If the context contains code examples, include them in your response using proper markdown formatting
- Use markdown code blocks with language identifiers (```python, ```bash, etc.)
- If the context doesn't contain enough information to answer the question, say so clearly
- Be concise but complete
- Structure your answer logically with headings or bullet points if appropriate

Answer:"""
            
            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            print(f"Gemini API error: {str(e)}")
            return None


# Global Gemini service instance
gemini_service = GeminiService()

