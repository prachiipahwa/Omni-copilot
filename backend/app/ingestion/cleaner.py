from bs4 import BeautifulSoup
import re

class TextCleaner:
    """Production-grade text cleaning isolating whitespace and stripping noisy HTML safely."""

    @staticmethod
    def strip_html(html_content: str) -> str:
        if not html_content:
            return ""
            
        soup = BeautifulSoup(html_content, "html.parser")
        
        # Strip script & style elements forcefully
        for script in soup(["script", "style", "noscript", "iframe"]):
            script.decompose()
            
        text = soup.get_text(separator="\n", strip=True)
        return text

    @staticmethod
    def normalize_whitespace(text: str) -> str:
        """Removes duplicate newlines mapping structural breaks natively."""
        if not text:
            return ""
        # Replace 3+ newlines with exactly 2
        text = re.sub(r'\n{3,}', '\n\n', text)
        # Replace multiple horizontal spaces
        text = re.sub(r'[ \t]+', ' ', text)
        return text.strip()
        
    @staticmethod
    def clean(content: str, is_html: bool = False) -> str:
        if is_html:
            content = TextCleaner.strip_html(content)
        return TextCleaner.normalize_whitespace(content)
