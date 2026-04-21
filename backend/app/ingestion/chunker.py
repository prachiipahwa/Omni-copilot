import tiktoken
from typing import List

class Chunker:
    """Configurable TikToken chunking supporting metadata encapsulation and context sliding windows."""
    
    def __init__(self, model: str = "cl100k_base", chunk_size: int = 400, overlap: int = 50):
        if chunk_size <= 0:
            raise ValueError("Chunk size must be greater than 0")
        if overlap < 0 or overlap >= chunk_size:
            raise ValueError("Overlap must be >= 0 and strictly less than chunk_size")
            
        self.encoder = tiktoken.get_encoding(model)
        self.chunk_size = chunk_size
        self.overlap = overlap

    def chunk_text(self, text: str) -> List[str]:
        if not text or not text.strip():
            return []
            
        tokens = self.encoder.encode(text)
        
        # Pathological guard: very small payloads don't need slicing
        if len(tokens) <= self.chunk_size:
            return [text.strip()]
            
        chunks = []
        start = 0
        while start < len(tokens):
            end = start + self.chunk_size
            chunk_tokens = tokens[start:end]
            chunks.append(self.encoder.decode(chunk_tokens).strip())
            
            # Slide window ensuring we catch semantic overlap cleanly
            start += self.chunk_size - self.overlap
                
        return chunks
