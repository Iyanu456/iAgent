import os
import binascii
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import padding
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Ensure ENCRYPTION_KEY is exactly 32 bytes
ENCRYPTION_KEY = (os.getenv('ENCRYPTION_KEY', 'your-encryption-key').ljust(32, '0'))[:32].encode('utf-8')
IV_LENGTH = 16  # Initialization vector length


def encrypt(text: str) -> str:
    """
    Encrypts a plaintext string using AES-256-CBC.

    Args:
        text (str): The plaintext to encrypt.

    Returns:
        str: The encrypted string in the format 'iv:encrypted_data', both in hex format.
    """
    # Generate a random initialization vector (IV)
    iv = os.urandom(IV_LENGTH)

    # Create the cipher object
    cipher = Cipher(algorithms.AES(ENCRYPTION_KEY), modes.CBC(iv), backend=default_backend())
    encryptor = cipher.encryptor()

    # Pad the plaintext to match block size requirements
    padder = padding.PKCS7(algorithms.AES.block_size).padder()
    padded_data = padder.update(text.encode('utf-8')) + padder.finalize()

    # Encrypt the data
    encrypted = encryptor.update(padded_data) + encryptor.finalize()

    # Return the IV and encrypted data as hex-encoded strings
    return f"{binascii.hexlify(iv).decode('utf-8')}:{binascii.hexlify(encrypted).decode('utf-8')}"

"""
# Example usage
if __name__ == "__main__":
    plaintext = "0xd25f04fc0b4165a4e5be566c9689076bc8a3d6a934a7ba5548cbe14c98819e83"
    encrypted_text = encrypt(plaintext)
    print(f"Encrypted Text: {encrypted_text}")"""
