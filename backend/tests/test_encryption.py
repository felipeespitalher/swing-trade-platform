"""
Comprehensive tests for AES-256-GCM encryption manager.

Tests covering:
- Encryption/decryption round-trip
- Different IVs for same plaintext
- AAD authentication
- Error handling
- Multiple field encryption
"""

import pytest
from app.core.encryption import EncryptionManager


class TestEncryptionManagerInitialization:
    """Tests for EncryptionManager initialization."""

    def test_init_valid_master_key(self):
        """Test initialization with valid master key."""
        manager = EncryptionManager("test-master-key-12345")
        assert manager.key is not None
        assert len(manager.key) == 32  # 256 bits

    def test_init_empty_master_key(self):
        """Test initialization fails with empty master key."""
        with pytest.raises(ValueError, match="Master key must be a non-empty string"):
            EncryptionManager("")

    def test_init_none_master_key(self):
        """Test initialization fails with None master key."""
        with pytest.raises(ValueError, match="Master key must be a non-empty string"):
            EncryptionManager(None)

    def test_init_non_string_master_key(self):
        """Test initialization fails with non-string master key."""
        with pytest.raises(ValueError, match="Master key must be a non-empty string"):
            EncryptionManager(12345)

    def test_same_master_key_produces_same_derived_key(self):
        """Test that same master key produces same derived key (deterministic)."""
        manager1 = EncryptionManager("test-key")
        manager2 = EncryptionManager("test-key")
        assert manager1.key == manager2.key

    def test_different_master_keys_produce_different_derived_keys(self):
        """Test that different master keys produce different derived keys."""
        manager1 = EncryptionManager("test-key-1")
        manager2 = EncryptionManager("test-key-2")
        assert manager1.key != manager2.key


class TestEncryptionRoundTrip:
    """Tests for encryption and decryption round-trip."""

    @pytest.fixture
    def manager(self):
        """Create encryption manager for tests."""
        return EncryptionManager("test-master-key-12345")

    def test_encrypt_decrypt_simple_string(self, manager):
        """Test basic encryption and decryption."""
        plaintext = "my-secret-api-key-12345"
        encrypted = manager.encrypt(plaintext)
        decrypted = manager.decrypt(encrypted)
        assert decrypted == plaintext

    def test_encrypt_decrypt_with_special_chars(self, manager):
        """Test encryption with special characters."""
        plaintext = "!@#$%^&*()_+-=[]{}|;:',.<>?/\\"
        encrypted = manager.encrypt(plaintext)
        decrypted = manager.decrypt(encrypted)
        assert decrypted == plaintext

    def test_encrypt_decrypt_with_unicode(self, manager):
        """Test encryption with unicode characters."""
        plaintext = "こんにちは世界🔐密钥"
        encrypted = manager.encrypt(plaintext)
        decrypted = manager.decrypt(encrypted)
        assert decrypted == plaintext

    def test_encrypt_decrypt_long_string(self, manager):
        """Test encryption with very long plaintext."""
        plaintext = "x" * 10000
        encrypted = manager.encrypt(plaintext)
        decrypted = manager.decrypt(encrypted)
        assert decrypted == plaintext

    def test_encrypt_empty_string(self, manager):
        """Test encryption fails with empty plaintext."""
        with pytest.raises(ValueError, match="Plaintext cannot be empty"):
            manager.encrypt("")

    def test_decrypt_empty_string(self, manager):
        """Test decryption fails with empty encrypted string."""
        with pytest.raises(ValueError, match="Encrypted data cannot be empty"):
            manager.decrypt("")

    def test_decrypt_corrupted_data(self, manager):
        """Test decryption fails with corrupted ciphertext."""
        plaintext = "test-data"
        encrypted = manager.encrypt(plaintext)
        # Corrupt the encrypted data
        corrupted = encrypted[:-10] + "0000000000"
        with pytest.raises(ValueError, match="Decryption failed"):
            manager.decrypt(corrupted)

    def test_decrypt_with_wrong_aad(self, manager):
        """Test decryption fails when AAD doesn't match."""
        plaintext = "test-data"
        encrypted = manager.encrypt(plaintext, aad="user-123")
        # Try to decrypt with different AAD
        with pytest.raises(ValueError, match="Decryption failed"):
            manager.decrypt(encrypted, aad="user-456")

    def test_decrypt_aad_is_optional(self, manager):
        """Test that AAD is truly optional."""
        plaintext = "test-data"
        # Encrypt without AAD
        encrypted = manager.encrypt(plaintext)
        # Decrypt without AAD
        decrypted = manager.decrypt(encrypted)
        assert decrypted == plaintext


class TestEncryptionRandomness:
    """Tests for IV randomness and ciphertext variation."""

    @pytest.fixture
    def manager(self):
        """Create encryption manager for tests."""
        return EncryptionManager("test-master-key-12345")

    def test_different_ivs_for_same_plaintext(self, manager):
        """Test that same plaintext produces different ciphertexts (different IVs)."""
        plaintext = "api-key-test-data"
        encrypted1 = manager.encrypt(plaintext)
        encrypted2 = manager.encrypt(plaintext)
        # Different IVs should produce different ciphertexts
        assert encrypted1 != encrypted2

    def test_many_encryptions_all_different(self, manager):
        """Test that many encryptions all produce different ciphertexts."""
        plaintext = "same-api-key"
        ciphertexts = [manager.encrypt(plaintext) for _ in range(100)]
        # All ciphertexts should be unique
        assert len(set(ciphertexts)) == 100

    def test_iv_included_in_ciphertext(self, manager):
        """Test that IV is included in encrypted output (first 12 bytes when decoded)."""
        import base64
        plaintext = "test-data"
        encrypted = manager.encrypt(plaintext)
        # Decrypt to verify IV is included
        encrypted_bytes = base64.b64decode(encrypted)
        assert len(encrypted_bytes) >= manager.IV_SIZE

    def test_different_plaintexts_produce_different_ciphertexts(self, manager):
        """Test that different plaintexts produce different ciphertexts."""
        encrypted1 = manager.encrypt("api-key-1")
        encrypted2 = manager.encrypt("api-key-2")
        assert encrypted1 != encrypted2


class TestEncryptionWithAAD:
    """Tests for Additional Authenticated Data (AAD) security."""

    @pytest.fixture
    def manager(self):
        """Create encryption manager for tests."""
        return EncryptionManager("test-master-key-12345")

    def test_encrypt_decrypt_with_aad_matches(self, manager):
        """Test encryption/decryption with matching AAD."""
        plaintext = "secret-api-key"
        aad = "user-id-123"
        encrypted = manager.encrypt(plaintext, aad=aad)
        decrypted = manager.decrypt(encrypted, aad=aad)
        assert decrypted == plaintext

    def test_aad_prevents_key_swapping(self, manager):
        """Test that AAD prevents decryption with different user IDs."""
        plaintext = "shared-secret"
        # Encrypt with user A's ID as AAD
        encrypted_for_user_a = manager.encrypt(plaintext, aad="user-a")
        # Try to decrypt with user B's ID as AAD
        with pytest.raises(ValueError, match="Decryption failed"):
            manager.decrypt(encrypted_for_user_a, aad="user-b")

    def test_aad_none_and_empty_string_treated_same(self, manager):
        """Test that None AAD and empty string AAD are treated the same."""
        plaintext = "test-data"
        encrypted_no_aad = manager.encrypt(plaintext, aad=None)
        encrypted_empty_aad = manager.encrypt(plaintext, aad="")
        # None and empty string are both treated as no AAD
        # Decrypt with None should work for both
        assert manager.decrypt(encrypted_no_aad, aad=None) == plaintext
        assert manager.decrypt(encrypted_empty_aad, aad=None) == plaintext
        # Decrypt with empty string should work for both
        assert manager.decrypt(encrypted_no_aad, aad="") == plaintext
        assert manager.decrypt(encrypted_empty_aad, aad="") == plaintext

    def test_aad_case_sensitive(self, manager):
        """Test that AAD is case-sensitive."""
        plaintext = "test-data"
        encrypted = manager.encrypt(plaintext, aad="UserID123")
        # Different case should fail
        with pytest.raises(ValueError, match="Decryption failed"):
            manager.decrypt(encrypted, aad="userid123")

    def test_aad_whitespace_matters(self, manager):
        """Test that AAD whitespace is significant."""
        plaintext = "test-data"
        encrypted = manager.encrypt(plaintext, aad="user 123")
        # Extra whitespace should fail
        with pytest.raises(ValueError, match="Decryption failed"):
            manager.decrypt(encrypted, aad="user  123")


class TestMultipleFieldEncryption:
    """Tests for encrypting multiple fields at once."""

    @pytest.fixture
    def manager(self):
        """Create encryption manager for tests."""
        return EncryptionManager("test-master-key-12345")

    def test_encrypt_multiple_fields(self, manager):
        """Test encrypting multiple fields in one call."""
        data = {
            "api_key": "binance-api-key-12345",
            "api_secret": "binance-secret-67890"
        }
        encrypted_data = manager.encrypt_multiple(data)
        assert len(encrypted_data) == 2
        assert "api_key" in encrypted_data
        assert "api_secret" in encrypted_data
        # Values should be encrypted (different from originals)
        assert encrypted_data["api_key"] != data["api_key"]
        assert encrypted_data["api_secret"] != data["api_secret"]

    def test_decrypt_multiple_fields(self, manager):
        """Test decrypting multiple fields in one call."""
        original_data = {
            "api_key": "binance-api-key-12345",
            "api_secret": "binance-secret-67890"
        }
        encrypted_data = manager.encrypt_multiple(original_data)
        decrypted_data = manager.decrypt_multiple(encrypted_data)
        assert decrypted_data == original_data

    def test_encrypt_decrypt_multiple_with_aad(self, manager):
        """Test encrypt/decrypt multiple with AAD."""
        original_data = {
            "api_key": "key-123",
            "api_secret": "secret-456"
        }
        aad = "user-789"
        encrypted_data = manager.encrypt_multiple(original_data, aad=aad)
        decrypted_data = manager.decrypt_multiple(encrypted_data, aad=aad)
        assert decrypted_data == original_data

    def test_encrypt_multiple_empty_dict(self, manager):
        """Test encrypting empty dictionary."""
        data = {}
        encrypted_data = manager.encrypt_multiple(data)
        assert encrypted_data == {}


class TestEncryptionConstants:
    """Tests for encryption parameters and constants."""

    def test_iv_size_is_12_bytes(self):
        """Test that IV size is 12 bytes (96 bits) for GCM."""
        assert EncryptionManager.IV_SIZE == 12

    def test_iterations_is_100000(self):
        """Test that PBKDF2 uses 100,000 iterations (NIST recommended)."""
        assert EncryptionManager.ITERATIONS == 100000

    def test_key_derivation_produces_256_bit_key(self):
        """Test that key derivation produces 256-bit key."""
        manager = EncryptionManager("test-key")
        assert len(manager.key) == 32  # 256 bits = 32 bytes


class TestEncryptionEdgeCases:
    """Tests for edge cases and boundary conditions."""

    @pytest.fixture
    def manager(self):
        """Create encryption manager for tests."""
        return EncryptionManager("test-master-key-12345")

    def test_encrypt_single_character(self, manager):
        """Test encryption of single character."""
        plaintext = "a"
        encrypted = manager.encrypt(plaintext)
        decrypted = manager.decrypt(encrypted)
        assert decrypted == plaintext

    def test_encrypt_whitespace_only(self, manager):
        """Test encryption of whitespace-only string."""
        plaintext = "   \t\n  "
        encrypted = manager.encrypt(plaintext)
        decrypted = manager.decrypt(encrypted)
        assert decrypted == plaintext

    def test_encrypt_very_long_aad(self, manager):
        """Test encryption with very long AAD."""
        plaintext = "test-data"
        aad = "x" * 10000
        encrypted = manager.encrypt(plaintext, aad=aad)
        decrypted = manager.decrypt(encrypted, aad=aad)
        assert decrypted == plaintext

    def test_master_key_with_special_chars(self):
        """Test initialization with special characters in master key."""
        master_key = "!@#$%^&*()_+-=[]{}|;:',.<>?/\\"
        manager = EncryptionManager(master_key)
        plaintext = "test-data"
        encrypted = manager.encrypt(plaintext)
        decrypted = manager.decrypt(encrypted)
        assert decrypted == plaintext

    def test_master_key_unicode(self):
        """Test initialization with unicode master key."""
        master_key = "مفتاح密钥🔐"
        manager = EncryptionManager(master_key)
        plaintext = "test-data"
        encrypted = manager.encrypt(plaintext)
        decrypted = manager.decrypt(encrypted)
        assert decrypted == plaintext
