# encryption_utils.py
import os
import json
import logging
from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy.types import TypeDecorator, Text

# --- Environment Variable and Fernet Initialization ---
ENCRYPTION_KEY_ENV_VAR = "ENV_ENCRYPTION_KEY"
_encryption_key_str = os.environ.get(ENCRYPTION_KEY_ENV_VAR)

if not _encryption_key_str:
    raise ValueError(
        f"ERROR: Required environment variable '{ENCRYPTION_KEY_ENV_VAR}' is not set. "
        "Please generate a key and set the variable."
        "\nGeneration command: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\"" # noqa
    )

try:
    _fernet = Fernet(_encryption_key_str.encode('utf-8'))
    logging.info(f"Fernet encryption initialized using key from {ENCRYPTION_KEY_ENV_VAR}.")
except (ValueError, TypeError) as e:
    raise ValueError(
        f"ERROR: Invalid encryption key format in environment variable '{ENCRYPTION_KEY_ENV_VAR}'. "
        f"Ensure it's a valid Fernet key. Original error: {e}"
    ) from e

# --- SQLAlchemy Type Decorator ---

class EncryptedJSON(TypeDecorator):
    """Encrypts/Decrypts JSON data stored in a TEXT column using Fernet."""
    impl = Text
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if not isinstance(value, dict):
             raise TypeError("EncryptedJSON requires a dictionary value.")

        try:
            json_string = json.dumps(value)
            encrypted_bytes = _fernet.encrypt(json_string.encode('utf-8'))
            return encrypted_bytes.decode('utf-8') # Store as string
        except Exception as e:
            logging.error(f"Encryption failed: {e}", exc_info=True)
            raise ValueError(f"Could not encrypt data: {e}") from e

    def process_result_value(self, value, dialect):
        if value is None:
            return None

        try:
            decrypted_bytes = _fernet.decrypt(value.encode('utf-8'))
            json_string = decrypted_bytes.decode('utf-8')
            return json.loads(json_string)
        except InvalidToken:
            logging.error("Decryption failed: Invalid token (wrong key or corrupt data).")
            raise ValueError("Failed to decrypt data: Invalid token or key.")
        except Exception as e:
            logging.error(f"Decryption or JSON parsing failed: {e}", exc_info=True)
            raise ValueError(f"Could not decrypt or parse data: {e}") from e