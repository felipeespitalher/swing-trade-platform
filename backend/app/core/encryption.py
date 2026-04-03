"""
AES-256-GCM encryption manager for sensitive data.

Provides symmetric encryption with authenticated data (AAD) support
to secure exchange API keys in the database.
"""

import os
import base64
from typing import Optional

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


class EncryptionManager:
    """
    AES-256-GCM encryption manager for securing API keys.

    Features:
    - AES-256-GCM authenticated encryption
    - Random 96-bit IV per encryption (no IV reuse)
    - PBKDF2 key derivation with 100,000 iterations (NIST recommended)
    - AAD (Additional Authenticated Data) support for additional security
    - Base64 encoding for database storage

    Security notes:
    - Each encryption generates a new random IV
    - Different plaintexts encrypted with same master key produce different ciphertexts
    - AAD prevents key substitution attacks
    - IV is included in ciphertext output for decryption
    """

    # Salt for PBKDF2 key derivation
    # This is intentionally fixed (not random) as it's only for key derivation
    SALT = b"swing-trade-encryption-salt-v1"

    # NIST recommends at least 100,000 iterations as of 2023
    ITERATIONS = 100000

    # IV size for GCM: 96 bits (12 bytes) - recommended for performance and security
    IV_SIZE = 12

    # GCM tag size: 128 bits (16 bytes) - maximum authentication strength
    TAG_SIZE = 128

    def __init__(self, master_key: str):
        """
        Initialize the encryption manager with a master key.

        The master key is derived using PBKDF2-SHA256 to create a 256-bit key
        suitable for AES-256 encryption.

        Args:
            master_key: The master encryption key (string)

        Raises:
            ValueError: If master_key is empty or invalid
        """
        if not master_key or not isinstance(master_key, str):
            raise ValueError("Master key must be a non-empty string")

        # Derive a 256-bit key from the master key using PBKDF2
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,  # 256 bits for AES-256
            salt=self.SALT,
            iterations=self.ITERATIONS,
        )
        self.key = kdf.derive(master_key.encode("utf-8"))

    def encrypt(self, plaintext: str, aad: Optional[str] = None) -> str:
        """
        Encrypt plaintext using AES-256-GCM with random IV.

        The output format is: base64(iv + ciphertext + tag)
        This allows the IV to be stored alongside the ciphertext.

        Args:
            plaintext: The data to encrypt (string)
            aad: Optional Additional Authenticated Data (e.g., user_id)
                 Prevents ciphertext swapping between users

        Returns:
            Base64-encoded encrypted data including IV

        Raises:
            ValueError: If plaintext is empty
            Exception: If encryption fails
        """
        if not plaintext:
            raise ValueError("Plaintext cannot be empty")

        # Generate a random 96-bit IV for this encryption
        iv = os.urandom(self.IV_SIZE)

        # Create cipher instance
        cipher = AESGCM(self.key)

        # Prepare AAD if provided
        aad_bytes = aad.encode("utf-8") if aad else None

        # Encrypt: produces ciphertext + authentication tag
        ciphertext = cipher.encrypt(iv, plaintext.encode("utf-8"), aad_bytes)

        # Combine IV + ciphertext + tag for storage
        # Format: [IV (12 bytes)][CIPHERTEXT + TAG (variable)]
        encrypted_data = iv + ciphertext

        # Base64 encode for storage in text fields
        return base64.b64encode(encrypted_data).decode("utf-8")

    def decrypt(self, encrypted: str, aad: Optional[str] = None) -> str:
        """
        Decrypt AES-256-GCM encrypted data.

        The encrypted parameter should be base64-encoded data containing
        IV + ciphertext + tag in that order.

        Args:
            encrypted: Base64-encoded encrypted data (from encrypt method)
            aad: Optional Additional Authenticated Data (must match encryption AAD)
                 If AAD was used during encryption, must be provided here

        Returns:
            Decrypted plaintext as string

        Raises:
            ValueError: If encrypted data is invalid or corrupted
            Exception: If decryption fails (wrong AAD or corrupted data)
        """
        if not encrypted:
            raise ValueError("Encrypted data cannot be empty")

        try:
            # Decode from base64
            encrypted_bytes = base64.b64decode(encrypted)

            # Extract IV from first 12 bytes
            if len(encrypted_bytes) < self.IV_SIZE:
                raise ValueError("Encrypted data too short - missing IV")

            iv = encrypted_bytes[: self.IV_SIZE]
            ciphertext = encrypted_bytes[self.IV_SIZE :]

            # Prepare AAD if provided
            aad_bytes = aad.encode("utf-8") if aad else None

            # Create cipher instance
            cipher = AESGCM(self.key)

            # Decrypt and verify authentication tag
            plaintext = cipher.decrypt(iv, ciphertext, aad_bytes)

            return plaintext.decode("utf-8")

        except Exception as e:
            raise ValueError(f"Decryption failed: {str(e)}")

    def encrypt_multiple(
        self, data_dict: dict[str, str], aad: Optional[str] = None
    ) -> dict[str, str]:
        """
        Encrypt multiple string values in a dictionary.

        Useful for encrypting multiple fields of an API key (e.g., api_key and api_secret).

        Args:
            data_dict: Dictionary of {field_name: plaintext_value}
            aad: Optional Additional Authenticated Data

        Returns:
            Dictionary of {field_name: encrypted_value}
        """
        return {key: self.encrypt(value, aad) for key, value in data_dict.items()}

    def decrypt_multiple(
        self, data_dict: dict[str, str], aad: Optional[str] = None
    ) -> dict[str, str]:
        """
        Decrypt multiple encrypted values in a dictionary.

        Args:
            data_dict: Dictionary of {field_name: encrypted_value}
            aad: Optional Additional Authenticated Data

        Returns:
            Dictionary of {field_name: plaintext_value}
        """
        return {key: self.decrypt(value, aad) for key, value in data_dict.items()}
