-- Create exchange_keys table for storing encrypted API credentials
-- Part of Task P1-5: AES-256-GCM encryption layer for API keys

CREATE TABLE IF NOT EXISTS exchange_keys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    exchange VARCHAR(50) NOT NULL,
    api_key_encrypted TEXT NOT NULL,
    api_secret_encrypted TEXT NOT NULL,
    encryption_iv VARCHAR(50) NOT NULL DEFAULT 'v1',
    is_testnet BOOLEAN NOT NULL DEFAULT TRUE,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Create unique constraint for user_id, exchange, is_testnet combination
ALTER TABLE exchange_keys
ADD CONSTRAINT uq_user_exchange_testnet
UNIQUE (user_id, exchange, is_testnet);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_exchange_keys_user ON exchange_keys(user_id);
CREATE INDEX IF NOT EXISTS idx_exchange_keys_active ON exchange_keys(is_active);
CREATE INDEX IF NOT EXISTS idx_exchange_keys_exchange ON exchange_keys(exchange);
CREATE INDEX IF NOT EXISTS idx_exchange_keys_created ON exchange_keys(created_at);

-- Add comment to describe the encryption
COMMENT ON TABLE exchange_keys IS 'Store encrypted exchange API credentials (AES-256-GCM)';
COMMENT ON COLUMN exchange_keys.api_key_encrypted IS 'API key encrypted with AES-256-GCM using PBKDF2-derived key';
COMMENT ON COLUMN exchange_keys.api_secret_encrypted IS 'API secret encrypted with AES-256-GCM using PBKDF2-derived key';
COMMENT ON COLUMN exchange_keys.encryption_iv IS 'Encryption version tag (for future key rotation)';
