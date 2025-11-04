"""
Query Enhancement Service

Uses LLM to expand/rewrite queries before vector search.
This helps improve retrieval by:
- Generating keywords and synonyms
- Rewriting queries for better semantic matching
- Extracting key concepts
- Expanding abbreviations and context
"""

from typing import List, Dict, Optional
from app.services.gemini import gemini_service


class QueryEnhancer:
    """Enhances queries using LLM before vector search"""
    
    def __init__(self):
        self.gemini_service = gemini_service
    
    def enhance_query(
        self, 
        original_query: str,
        context: Optional[str] = None
    ) -> Dict[str, any]:
        """
        Enhance query using LLM to generate better search terms.
        
        Returns:
            {
                "enhanced_query": str,  # Main enhanced query
                "keywords": List[str],  # Key terms to search for
                "synonyms": List[str],  # Related terms
                "concepts": List[str],  # Key concepts
                "query_type": str,  # "definition", "how-to", "example", etc.
                "search_strategy": str  # "broad", "specific", "hybrid"
            }
        """
        if not self.gemini_service.enabled:
            # Fallback: return original query
            return {
                "enhanced_query": original_query,
                "keywords": self._extract_keywords_simple(original_query),
                "synonyms": [],
                "concepts": self._extract_keywords_simple(original_query),
                "query_type": self._detect_query_type_simple(original_query),
                "search_strategy": "broad"
            }
        
        try:
            # Build prompt for query enhancement
            prompt = self._build_enhancement_prompt(original_query, context)
            
            # Call Gemini to enhance query
            if not self.gemini_service.model:
                raise Exception("Gemini model not available")
            
            response = self.gemini_service.model.generate_content(prompt)
            
            # Extract text from response
            if hasattr(response, 'text'):
                response_text = response.text
            elif hasattr(response, 'candidates') and len(response.candidates) > 0:
                response_text = response.candidates[0].content.parts[0].text
            else:
                response_text = str(response)
            
            # Parse response
            enhanced_data = self._parse_enhancement_response(response_text)
            
            # Ensure we have all required fields
            enhanced_data.setdefault("enhanced_query", original_query)
            enhanced_data.setdefault("keywords", [])
            enhanced_data.setdefault("synonyms", [])
            enhanced_data.setdefault("concepts", [])
            enhanced_data.setdefault("query_type", "general")
            enhanced_data.setdefault("search_strategy", "broad")
            
            # Set defaults for new fields
            enhanced_data.setdefault("required_topics", [])
            enhanced_data.setdefault("recommended_top_k", 5)
            enhanced_data.setdefault("multi_query_needed", False)
            
            # If query seems to need multiple topics but not set, analyze it
            if not enhanced_data.get("required_topics"):
                enhanced_data["required_topics"] = self._analyze_required_topics(original_query)
            
            # Auto-detect multi-query need based on topics
            if len(enhanced_data.get("required_topics", [])) > 1:
                enhanced_data["multi_query_needed"] = True
                # Increase top_k if multiple topics
                if enhanced_data.get("recommended_top_k", 5) <= 5:
                    enhanced_data["recommended_top_k"] = len(enhanced_data["required_topics"]) * 3
            
            return enhanced_data
            
        except Exception as e:
            print(f"Error enhancing query: {e}")
            # Fallback to simple enhancement
            return {
                "enhanced_query": original_query,
                "keywords": self._extract_keywords_simple(original_query),
                "synonyms": [],
                "concepts": self._extract_keywords_simple(original_query),
                "query_type": self._detect_query_type_simple(original_query),
                "search_strategy": "broad"
            }
    
    def _build_enhancement_prompt(self, query: str, context: Optional[str] = None) -> str:
        """Build prompt for LLM to enhance query and determine retrieval strategy"""
        prompt = f"""You are a query enhancement system for a RAG (Retrieval Augmented Generation) system. 
Your task is to enhance a user query and determine how to retrieve information from multiple sections of documentation.

Original Query: "{query}"

Please analyze this query and provide:
1. An enhanced/rewritten query that would be better for semantic search
2. Key keywords and important terms
3. Synonyms and related terms
4. Main concepts to search for
5. Query type (definition, how-to, example, comparison, troubleshooting, multi-step, etc.)
6. Search strategy (broad, specific, or hybrid)
7. **REQUIRED TOPICS**: List of different topics/sections that need to be retrieved (e.g., ["customer creation", "payment charging", "error handling"])
8. **RECOMMENDED_TOP_K**: Suggested number of chunks to fetch (default: 5, but increase if multiple topics are needed)
9. **MULTI_QUERY_NEEDED**: Whether to use multiple targeted searches for different topics (true/false)

Consider:
- If the query asks "what is X?", also search for "X definition", "X overview", "X introduction"
- If the query asks "how to", also search for "steps", "tutorial", "guide", "example"
- If the query requires multiple steps or combines multiple concepts (e.g., "create customer AND charge them"), you need MULTIPLE TOPICS
- For multi-step queries, increase recommended_top_k to ensure all topics are covered
- Extract technical terms and their common variations
- Include acronyms and their full forms
- Consider context if provided

Examples:
- Query: "Write code to create customer and charge them" 
  → required_topics: ["customer creation", "payment charging", "error handling"]
  → recommended_top_k: 10 (need more chunks for multiple topics)
  → multi_query_needed: true

- Query: "What is FastAPI?"
  → required_topics: ["FastAPI definition"]
  → recommended_top_k: 5
  → multi_query_needed: false

Respond in JSON format:
{{
    "enhanced_query": "rewritten query with better semantic meaning",
    "keywords": ["key", "terms", "to", "search"],
    "synonyms": ["related", "terms", "synonyms"],
    "concepts": ["main", "concepts", "to", "find"],
    "query_type": "definition|how-to|example|comparison|troubleshooting|multi-step|general",
    "search_strategy": "broad|specific|hybrid",
    "required_topics": ["topic1", "topic2", "topic3"],
    "recommended_top_k": 10,
    "multi_query_needed": true,
    "reasoning": "brief explanation of enhancements"
}}

Be concise but thorough. Focus on terms that would improve vector search results.
"""
        
        if context:
            prompt += f"\n\nContext (available document information):\n{context[:500]}"
        
        return prompt
    
    def _parse_enhancement_response(self, response_text: str) -> Dict:
        """Parse LLM response to extract enhancement data"""
        import json
        import re
        
        # Try to extract JSON from response
        # Sometimes LLM wraps JSON in markdown or adds extra text
        json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
        if json_match:
            try:
                data = json.loads(json_match.group())
                return data
            except json.JSONDecodeError:
                pass
        
        # Fallback: try to parse as is
        try:
            data = json.loads(response_text)
            return data
        except json.JSONDecodeError:
            pass
        
        # Last resort: extract what we can from text
        return self._extract_from_text(response_text)
    
    def _extract_from_text(self, text: str) -> Dict:
        """Extract enhancement data from plain text response"""
        enhanced_query = text.split('\n')[0] if text else ""
        
        return {
            "enhanced_query": enhanced_query,
            "keywords": self._extract_keywords_simple(enhanced_query),
            "synonyms": [],
            "concepts": self._extract_keywords_simple(enhanced_query),
            "query_type": "general",
            "search_strategy": "broad"
        }
    
    def _extract_keywords_simple(self, query: str) -> List[str]:
        """Simple keyword extraction (fallback)"""
        # Remove common stop words
        stop_words = {'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been', 
                     'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 
                     'would', 'should', 'could', 'can', 'may', 'might', 'must', 
                     'what', 'when', 'where', 'why', 'how', 'who', 'which', 
                     'this', 'that', 'these', 'those', 'to', 'for', 'of', 'in', 
                     'on', 'at', 'by', 'from', 'as', 'with', 'about', 'into', 
                     'through', 'during', 'including', 'against', 'among'}
        
        # Extract words
        words = query.lower().split()
        keywords = [w for w in words if w not in stop_words and len(w) > 2]
        
        return keywords[:10]  # Limit to top 10
    
    def _detect_query_type_simple(self, query: str) -> str:
        """Simple query type detection (fallback)"""
        query_lower = query.lower()
        
        # Check for multi-step queries (contains "and", "then", "also", multiple action verbs)
        action_verbs = ['create', 'make', 'add', 'charge', 'process', 'handle', 'include']
        action_count = sum(1 for verb in action_verbs if verb in query_lower)
        if action_count > 1 or any(word in query_lower for word in [' and ', ' then ', ' also ', ' plus ']):
            return "multi-step"
        
        if any(word in query_lower for word in ['what is', 'what are', 'define', 'definition', 'explain']):
            return "definition"
        elif any(word in query_lower for word in ['how to', 'how do', 'how can', 'steps', 'tutorial']):
            return "how-to"
        elif any(word in query_lower for word in ['example', 'sample', 'code', 'snippet']):
            return "example"
        elif any(word in query_lower for word in ['compare', 'difference', 'vs', 'versus']):
            return "comparison"
        elif any(word in query_lower for word in ['error', 'fix', 'issue', 'problem', 'troubleshoot']):
            return "troubleshooting"
        else:
            return "general"
    
    def _analyze_required_topics(self, query: str) -> List[str]:
        """Analyze query to determine required topics (fallback)"""
        query_lower = query.lower()
        topics = []
        
        # Detect customer-related topics
        if any(word in query_lower for word in ['customer', 'create customer', 'new customer']):
            topics.append("customer creation")
        
        # Detect payment-related topics
        if any(word in query_lower for word in ['payment', 'charge', 'charge them', 'pay', 'amount', '$']):
            topics.append("payment charging")
        
        # Detect error handling
        if any(word in query_lower for word in ['error', 'error handling', 'try', 'catch', 'exception']):
            topics.append("error handling")
        
        # Detect subscription-related
        if 'subscription' in query_lower:
            topics.append("subscription")
        
        # Detect webhook-related
        if 'webhook' in query_lower:
            topics.append("webhooks")
        
        # If no specific topics found, return general
        if not topics:
            topics.append("general")
        
        return topics
    
    def get_search_queries(self, enhanced_data: Dict) -> List[str]:
        """
        Generate multiple search queries from enhanced data.
        Returns list of queries to try (for multi-query retrieval).
        """
        queries = []
        
        # Primary enhanced query
        if enhanced_data.get("enhanced_query"):
            queries.append(enhanced_data["enhanced_query"])
        
        # Additional queries from keywords
        keywords = enhanced_data.get("keywords", [])
        if keywords:
            # Create query from keywords
            keyword_query = " ".join(keywords[:5])  # Top 5 keywords
            if keyword_query and keyword_query not in queries:
                queries.append(keyword_query)
        
        # Query from concepts
        concepts = enhanced_data.get("concepts", [])
        if concepts:
            concept_query = " ".join(concepts[:5])
            if concept_query and concept_query not in queries:
                queries.append(concept_query)
        
        return queries if queries else [enhanced_data.get("enhanced_query", "")]
    
    def build_hybrid_search_query(self, enhanced_data: Dict, original_query: str) -> str:
        """
        Build a hybrid search query that combines original and enhanced terms.
        This query will be used for vector search.
        """
        enhanced = enhanced_data.get("enhanced_query", original_query)
        
        # Combine keywords and concepts for better coverage
        keywords = enhanced_data.get("keywords", [])
        concepts = enhanced_data.get("concepts", [])
        
        # Build comprehensive query
        all_terms = [enhanced]
        if keywords:
            all_terms.extend(keywords[:3])  # Top 3 keywords
        if concepts:
            all_terms.extend(concepts[:3])  # Top 3 concepts
        
        # Combine into single query
        hybrid_query = " ".join(set(all_terms))  # Remove duplicates
        
        # Fallback to original if nothing worked
        return hybrid_query if hybrid_query else original_query


# Global instance
query_enhancer = QueryEnhancer()

