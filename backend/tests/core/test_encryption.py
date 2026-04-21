import pytest
from app.core.encryption import encrypt_dict, decrypt_dict

def test_encryption_cycle():
    original_data = {"refresh_token": "1/abc123xyz", "scope": "drive"}
    
    # Encrypt
    encrypted_payload = encrypt_dict(original_data)
    
    # Assert string output and not easily readable
    assert isinstance(encrypted_payload, str)
    assert "refresh_token" not in encrypted_payload
    assert "1/abc123xyz" not in encrypted_payload
    
    # Decrypt
    decrypted_data = decrypt_dict(encrypted_payload)
    
    # Assert equality
    assert decrypted_data == original_data

def test_decryption_failure():
    with pytest.raises(ValueError, match="Invalid encryption token or key changed"):
        decrypt_dict("bad_cipher_text")
