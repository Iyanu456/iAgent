import os
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
import binascii
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Ensure ENCRYPTION_KEY is retrieved from the environment variable
ENCRYPTION_KEY = os.environ.get('ENCRYPTION_KEY')
if ENCRYPTION_KEY is None:
    raise ValueError("ENCRYPTION_KEY not found in environment variables")

# Convert to bytes and ensure it's 32 bytes long
ENCRYPTION_KEY = ENCRYPTION_KEY.ljust(32, '0')[:32].encode('utf-8')

IV_LENGTH = 16  # Initialization vector length

def decrypt(encrypted_text: str) -> str:
    try:
        # Split the input into the IV and encrypted text parts
        iv_hex, encrypted_hex = encrypted_text.split(':')
    except ValueError:
        print(f"Error: The encrypted text format is invalid. Expected 'iv:encrypted_text', got {encrypted_text}")
        raise

    # Convert hex values to bytes
    iv = binascii.unhexlify(iv_hex)
    encrypted = binascii.unhexlify(encrypted_hex)

    # Create the cipher object using AES-256-CBC
    cipher = Cipher(algorithms.AES(ENCRYPTION_KEY), modes.CBC(iv), backend=default_backend())
    decryptor = cipher.decryptor()

    # Decrypt the data
    decrypted = decryptor.update(encrypted) + decryptor.finalize()

    # Remove PKCS#7 padding manually
    padding_length = decrypted[-1]  # Last byte indicates padding length
    if padding_length > 16:  # Invalid padding
        raise ValueError("Invalid padding detected")
    decrypted = decrypted[:-padding_length]  # Remove padding bytes

    # Return the decrypted text as a string
    return decrypted.decode('utf-8')
"""
# Example usage
encrypted_private_key = "fb492742b0272b6e1f9a4073571d28c7:5bea5ad5f779231d9080dba78bba0edfb5a9f1c565d75093d0249a911777797d49129162ab9527c4e059e943cd2cdf7cf26108029aa7f961fc4f2d8420836e60f54918197e58a171650fc51235467d46"
try:
    private_key = decrypt(encrypted_private_key)
    print(f"Decrypted private key: {private_key}")
except Exception as e:
    print(f"Decryption failed: {str(e)}")"""
