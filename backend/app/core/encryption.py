import json
from cryptography.fernet import Fernet, InvalidToken
from app.core.config import settings
import structlog

logger = structlog.get_logger(__name__)

fernet = Fernet(settings.ENCRYPTION_KEY.encode() if settings.ENCRYPTION_KEY else Fernet.generate_key())

def encrypt_dict(data: dict) -> str:
    """Serialize and encrypt dictionary into a safe string payload (Ciphertext)."""
    try:
        json_data = json.dumps(data)
        return fernet.encrypt(json_data.encode()).decode()
    except Exception as e:
        logger.error("encryption_failed", error=str(e))
        raise ValueError("Failed to encrypt data")

def decrypt_dict(encrypted_str: str) -> dict:
    """Decrypt and deserialize payload back into dict."""
    try:
        decrypted_bytes = fernet.decrypt(encrypted_str.encode())
        return json.loads(decrypted_bytes.decode())
    except InvalidToken:
        logger.error("decryption_invalid_token")
        raise ValueError("Invalid encryption token or key changed")
    except Exception as e:
        logger.error("decryption_failed", error=str(e))
        raise ValueError("Failed to decrypt data")
