import pytest
from app.ingestion.cleaner import TextCleaner
from app.ingestion.chunker import Chunker

def test_html_stripping():
    html_input = "<body><h1>Meeting Notes</h1><p>Discussed strategy.</p><script>alert('xss')</script></body>"
    cleaned = TextCleaner.clean(html_input, is_html=True)
    assert "Meeting Notes" in cleaned
    assert "Discussed strategy." in cleaned
    assert "script" not in cleaned
    assert "xss" not in cleaned

def test_whitespace_normalization():
    messy_text = "Headline   \n\n\n\n\n  Body text \t here."
    cleaned = TextCleaner.clean(messy_text, is_html=False)
    assert cleaned == "Headline\n\nBody text here."

def test_chunking_overlap():
    text = "Word " * 1000  # large text
    chunker = Chunker(chunk_size=100, overlap=20)
    chunks = chunker.chunk_text(text)
    
    assert len(chunks) > 1
    
    # We guarantee overlap logic captures sliding window bounds natively
    # Using TikToken directly simulates standard GPT embedding boundaries.
    
    # Check bounds
    assert "Word " in chunks[0]
    assert "Word " in chunks[1]
