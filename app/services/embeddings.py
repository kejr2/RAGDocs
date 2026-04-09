import logging
from typing import List
import numpy as np
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Service for generating embeddings using dual models for text and code."""

    def __init__(self):
        self.text_model: SentenceTransformer | None = None
        self.code_model = None
        self._text_model_loaded = False
        self._code_model_loaded = False

    @property
    def models_ready(self) -> bool:
        """Check if both models are loaded."""
        return self._text_model_loaded and self._code_model_loaded

    def _load_text_model(self):
        """Lazy load text embedding model."""
        if not self._text_model_loaded:
            logger.info("Loading text embedding model (all-MiniLM-L6-v2)…")
            self.text_model = SentenceTransformer('all-MiniLM-L6-v2')
            self._text_model_loaded = True
            logger.info("Text embedding model loaded")

    def _load_code_model(self):
        """Lazy load code embedding model."""
        if not self._code_model_loaded:
            logger.info("Loading code embedding model (jinaai/jina-embeddings-v2-base-code)…")
            from transformers import AutoModel, AutoTokenizer
            import torch

            model_name = 'jinaai/jina-embeddings-v2-base-code'
            tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
            model = AutoModel.from_pretrained(model_name, trust_remote_code=True)

            class JinaCodeModel:
                def __init__(self, model, tokenizer):
                    self.model = model
                    self.tokenizer = tokenizer
                    self._target_device = torch.device('cpu')

                def encode(self, sentences, batch_size: int = 32,
                           convert_to_numpy=True, show_progress_bar=False, **kwargs):
                    import torch as _torch

                    def mean_pooling(model_output, attention_mask):
                        token_embeddings = model_output[0]
                        mask = attention_mask.unsqueeze(-1).expand(token_embeddings.size()).float()
                        return _torch.sum(token_embeddings * mask, 1) / _torch.clamp(mask.sum(1), min=1e-9)

                    all_embeddings = []
                    for i in range(0, len(sentences), batch_size):
                        batch = sentences[i:i + batch_size]
                        encoded = self.tokenizer(batch, padding=True, truncation=True, return_tensors='pt')
                        with _torch.no_grad():
                            output = self.model(**encoded)
                        emb = mean_pooling(output, encoded['attention_mask'])
                        emb = _torch.nn.functional.normalize(emb, p=2, dim=1)
                        all_embeddings.append(emb.numpy() if convert_to_numpy else emb)

                    return np.vstack(all_embeddings) if convert_to_numpy else _torch.cat(all_embeddings)

                def get_sentence_embedding_dimension(self):
                    return 768  # jina-embeddings-v2-base-code

            self.code_model = JinaCodeModel(model, tokenizer)
            self._code_model_loaded = True
            logger.info("Code embedding model loaded")

    def encode_text(self, texts: List[str], batch_size: int = 64) -> List[List[float]]:
        """Encode text content using the text model."""
        self._load_text_model()
        embeddings = self.text_model.encode(
            texts, convert_to_numpy=True, batch_size=batch_size, show_progress_bar=False
        )
        return embeddings.tolist()

    def encode_code(self, code_texts: List[str], batch_size: int = 32) -> List[List[float]]:
        """Encode code content using the code model."""
        self._load_code_model()
        embeddings = self.code_model.encode(
            code_texts, batch_size=batch_size, convert_to_numpy=True
        )
        return embeddings.tolist()

    def get_text_embedding_dim(self) -> int:
        """Get dimension of text embeddings."""
        self._load_text_model()
        return self.text_model.get_sentence_embedding_dimension()

    def get_code_embedding_dim(self) -> int:
        """Get dimension of code embeddings."""
        self._load_code_model()
        return self.code_model.get_sentence_embedding_dimension()


# Global embedding service instance
embedding_service = EmbeddingService()
