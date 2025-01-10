import os
import uuid
import json
import hashlib

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import padding
from base64 import b64encode, b64decode

from config import API_KEY


# Hash the API_KEY to create a 256-bit KEY
KEY = hashlib.sha256(API_KEY.encode('utf-8')).digest()
IV = b"\xba\n\x9fC\x15w\x8f*\x08s\xd5\xf7%G\xfd-"    # Static IV (Initialization Vector), 16 bytes for AES


def encrypt_data(data):
    """
    Encrypts the given data using AES encryption with a randomly generated IV.

    Args:
        data (dict): The data to be encrypted. The data will be converted into JSON format 
                     and then encrypted.

    Returns:
        dict: A dictionary containing the encrypted data and the IV (Initialization Vector).
    
    Notes:
        The data is first serialized to JSON and padded to make its length 
        a multiple of the AES block size (128 bits). AES encryption is performed 
        using CBC mode with a static IV.
    """
    try:
        # Convert the data to JSON and then encode it to bytes
        data_bytes = json.dumps(data).encode('utf-8')

        # Apply PKCS7 padding to ensure the data size is a multiple of block size
        padder = padding.PKCS7(128).padder()
        padded_data = padder.update(data_bytes) + padder.finalize()
        iv = IV

        # Initialize AES cipher in CBC mode with the KEY and generated IV
        cipher = Cipher(algorithms.AES(KEY), modes.CBC(iv), backend=default_backend())
        encryptor = cipher.encryptor()

        # Perform encryption
        encrypted_data = encryptor.update(padded_data) + encryptor.finalize()

        # Return encrypted data and IV as a dictionary
        return {
            "a1": b64encode(encrypted_data).decode('utf-8'),
            "a2": b64encode(iv).decode('utf-8')
        }

    except Exception as e:
        print(f"Error during encryption: {e}")
        return None


def decrypt_data(encrypted_data, iv):
    """
    Decrypts the encrypted data using AES decryption with the provided IV.

    Args:
        encrypted_data (str): The encrypted data (base64 encoded).
        iv (str): The IV used during encryption (base64 encoded).

    Returns:
        dict: The decrypted data (original data before encryption).
    """
    try:
        # Decode the base64 encoded encrypted data and IV
        encrypted_data_bytes = b64decode(encrypted_data)
        iv_bytes = b64decode(iv)

        # Initialize AES cipher in CBC mode with the KEY and provided IV
        cipher = Cipher(algorithms.AES(KEY), modes.CBC(iv_bytes), backend=default_backend())
        decryptor = cipher.decryptor()

        # Decrypt the data
        decrypted_data = decryptor.update(encrypted_data_bytes) + decryptor.finalize()

        # Remove PKCS7 padding
        unpadder = padding.PKCS7(128).unpadder()
        unpadded_data = unpadder.update(decrypted_data) + unpadder.finalize()

        # Convert bytes back to JSON
        return json.loads(unpadded_data.decode('utf-8'))

    except Exception as e:
        print(f"Error during decryption: {e}")
        return None