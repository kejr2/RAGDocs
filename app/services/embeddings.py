from sentence_transformers import SentenceTransformer
from typing import List
import numpy as np


class EmbeddingService:
    """Service for generating embeddings using dual models for text and code"""
    
    def __init__(self):
        self.text_model: SentenceTransformer | None = None
        self.code_model: SentenceTransformer | None = None
        self._text_model_loaded = False
        self._code_model_loaded = False
    
    @property
    def models_ready(self) -> bool:
        """Check if both models are loaded"""
        return self._text_model_loaded and self._code_model_loaded
    
    def _load_text_model(self):
        """Lazy load text embedding model"""
        if not self._text_model_loaded:
            print("Loading text embedding model (all-MiniLM-L6-v2)...")
            self.text_model = SentenceTransformer('all-MiniLM-L6-v2')
            self._text_model_loaded = True
            print("✅ Text embedding model loaded")
    
    def _load_code_model(self):
        """Lazy load code embedding model"""
        if not self._code_model_loaded:
            print("Loading code embedding model (jinaai/jina-embeddings-v2-base-code)...")
            # Jina model requires trust_remote_code - use AutoModel directly
            from transformers import AutoModel, AutoTokenizer
            import torch
            
            model_name = 'jinaai/jina-embeddings-v2-base-code'
            tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
            model = AutoModel.from_pretrained(model_name, trust_remote_code=True)
            
            # Wrap in SentenceTransformer-like interface
            class JinaCodeModel:
                def __init__(self, model, tokenizer):
                    self.model = model
                    self.tokenizer = tokenizer
                    self._target_device = torch.device('cpu')
                
                def encode(self, sentences, convert_to_numpy=True, show_progress_bar=False, **kwargs):
                    # Use mean pooling as per Jina model
                    def mean_pooling(model_output, attention_mask):
                        token_embeddings = model_output[0]
                        input_mask_expanded = attention_mask.unsqueeze(-1).expand(token_embeddings.size()).float()
                        return torch.sum(token_embeddings * input_mask_expanded, 1) / torch.clamp(input_mask_expanded.sum(1), min=1e-9)
                    
                    encoded_input = self.tokenizer(sentences, padding=True, truncation=True, return_tensors='pt')
                    with torch.no_grad():
                        model_output = self.model(**encoded_input)
                    
                    sentence_embeddings = mean_pooling(model_output, encoded_input['attention_mask'])
                    sentence_embeddings = torch.nn.functional.normalize(sentence_embeddings, p=2, dim=1)
                    
                    if convert_to_numpy:
                        return sentence_embeddings.numpy()
                    return sentence_embeddings
                
                def get_sentence_embedding_dimension(self):
                    return 768  # jina-embeddings-v2-base-code dimension
            
            self.code_model = JinaCodeModel(model, tokenizer)
            self._code_model_loaded = True
            print("✅ Code embedding model loaded")
    
    def encode_text(self, texts: List[str]) -> List[List[float]]:
        """Encode text content using text model"""
        self._load_text_model()
        embeddings = self.text_model.encode(texts, convert_to_numpy=True)
        return embeddings.tolist()
    
    def encode_code(self, code_texts: List[str]) -> List[List[float]]:
        """Encode code content using code model"""
        self._load_code_model()
        embeddings = self.code_model.encode(code_texts, convert_to_numpy=True)
        return embeddings.tolist()
    
    def get_text_embedding_dim(self) -> int:
        """Get dimension of text embeddings"""
        self._load_text_model()
        return self.text_model.get_sentence_embedding_dimension()
    
    def get_code_embedding_dim(self) -> int:
        """Get dimension of code embeddings"""
        self._load_code_model()
        return self.code_model.get_sentence_embedding_dimension()


# Global embedding service instance
embedding_service = EmbeddingService()

