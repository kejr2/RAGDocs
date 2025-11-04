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
            prompt = f"""You are an expert documentation assistant. Your task is to provide accurate, helpful answers using the provided context when available, and your general knowledge when the context is insufficient.

CONTEXT FROM DOCUMENTATION (may contain information from multiple sections):
{context}

USER QUESTION: {query}

CRITICAL INSTRUCTIONS FOR CODE GENERATION QUERIES:
If the user asks for "complete code" or "write code", you MUST:
1. Create ONE SINGLE, COMPLETE code example that combines all required pieces
2. Do NOT just list sources separately or show partial code
3. Combine code snippets from different sections into a working whole
4. Include all necessary imports, setup, and error handling
5. Make sure the code is ready to copy and use

IMPORTANT INSTRUCTIONS:
1. PRIMARY: Use the provided context as your main source of information when it contains relevant information.
2. SECONDARY: If the context is insufficient or doesn't contain the information needed, use your general knowledge to provide a complete answer.
3. PRIORITIZE: Always prefer context information when available, but don't limit yourself to only context if it's incomplete.
4. **Context Analysis**: The context may contain information from MULTIPLE DIFFERENT SECTIONS/TOPICS. 
   - Carefully review ALL sections of the context
   - If the context contains relevant information, use it as the primary source
   - Combine information from different sections if needed
   - If the query requires multiple steps (e.g., "create customer AND charge them"), 
     look for information about EACH step in different parts of the context
   - For code examples that combine multiple operations, piece together code from different sections
   - If context is missing key information, supplement with general knowledge
5. Look for:
   - Headings that match the question topic
   - Code examples related to the question (may be in different sections)
   - Step-by-step instructions if it's a "how-to" question
   - Definitions or explanations if it's a "what is" question
   - Error handling examples if the query asks for error handling
6. Include relevant code examples using proper markdown formatting (```language)
   - If you need to combine code from multiple sections, do so logically
   - Make sure the combined code is complete and functional
   - If context has partial code, complete it with general knowledge
7. **When context is available**: Use it as the foundation and supplement with general knowledge if needed to provide a complete answer.
8. **When context is insufficient**: Use your general knowledge to provide a complete, accurate answer. Do not say "I cannot find information" if you can answer from general knowledge.
9. **Balance**: Strive to provide complete, helpful answers by combining context (when available) with general knowledge (when needed).
10. Structure your answer logically:
   - Start with a direct answer if available
   - If multiple steps are required, organize by steps
   - Add supporting details
   - Include complete, working code examples if relevant
   - Include error handling if requested
11. Be specific and cite what you found in the context when using it.
12. **For multi-step queries**: Ensure your answer covers ALL required steps mentioned in the query.
   - Combine code snippets from different sections if needed
   - Make sure the final code is complete and handles all requirements
   - If you see code examples for different steps in different sections, combine them into one complete working example
   - For example, if you see "create customer" code in one section and "charge payment" code in another, combine them into a single flow

13. **IMPORTANT for code generation**: 
    - If the context contains code examples, USE THEM as the basis for your answer
    - If context has partial code, complete it using your knowledge of best practices
    - If context has no code but the query asks for code, provide complete code using general knowledge
    - Look carefully through ALL sections - code might be split across multiple chunks
    - Combine code snippets logically to create complete, working examples
    - Add error handling if requested, even if it's not in the same chunk as the main code
    - If the query asks for a specific language (e.g., "Node.js"), prioritize code in that language
    - If you see code in multiple languages, use the one that matches the query request
    - Create a SINGLE, COMPLETE code example that combines all required steps
    - Use general knowledge to ensure the code follows best practices and is complete

14. **For code combination**:
    - Do NOT just list the sources separately with "Source 1", "Source 2", etc.
    - Do NOT show multiple separate code blocks
    - CREATE ONE SINGLE, COMPLETE code example that combines all the pieces
    - Show the complete flow from start to finish in ONE code block
    - Include all necessary imports, setup, and error handling
    - Make sure the code is ready to use
    - Start with imports, then initialization, then the main logic, then error handling

15. **Response Format for Code Queries**:
    - If the query asks for "complete code" or "write code", provide ONLY the combined code
    - Do not include source citations or separate code blocks
    - Provide the complete code example in a single ```javascript or ```python block
    - Add brief comments explaining key steps

EXAMPLE: If user asks "Write complete Node.js code to create customer and charge them $50":
- DO: Provide one complete code block with customer creation + payment charging + error handling
- DON'T: List "Source 1: customer code", "Source 2: payment code" separately
- If context has partial code, complete it. If context has no code, provide complete code from general knowledge.

ANSWER (combining context information when available with general knowledge when needed):"""
            
            response = self.model.generate_content(
                prompt,
                generation_config={
                    "temperature": 0.3,  # Lower temperature for more focused answers
                    "top_p": 0.8,
                    "top_k": 40,
                    "max_output_tokens": 2048,
                }
            )
            return response.text
        except Exception as e:
            print(f"Gemini API error: {str(e)}")
            return None


# Global Gemini service instance
gemini_service = GeminiService()

