# Security

## Threat Model

### Who Attacks

- External adversaries attempting to access other users' trading data or credentials
- Automated bots performing credential stuffing or brute-force login attacks
- Authenticated users attempting to access resources belonging to other accounts
- Attackers attempting to forge requests on behalf of authenticated users (CSRF)

### What They Want

- API keys to exchanges (could be used to trade or drain accounts)
- Access tokens to impersonate users
- Strategy and trade data for competitive intelligence
- Ability to manipulate another user's positions or settings

---

## Security Controls

### Authentication

- **Mechanism**: JSON Web Tokens (JWT), algorithm HS256
- **Access token lifetime**: Configurable (default 60 minutes)
- **Refresh token lifetime**: Configurable (default 7 days)
- **Password requirements**: Minimum 8 characters with uppercase, lowercase, digit, and special character
- **Password hashing**: PBKDF2-SHA256 via passlib
- **Email verification**: Required before first login; tokens are single-use random secrets

### Encryption

- **Algorithm**: AES-256-GCM (authenticated encryption)
- **Key derivation**: PBKDF2-HMAC-SHA256 from the master key with a random per-encryption salt
- **IV/Nonce**: Randomly generated for every encryption operation (unique IV per record)
- **What is encrypted**: Exchange API keys and secrets at rest in the database
- **Scope**: Only encrypted values are stored; the plaintext is never persisted

### Authorization

- **PostgreSQL Row-Level Security**: 18 RLS policies enforce that every SELECT, INSERT, UPDATE, and DELETE only touches rows owned by the current user
- **Application context**: `SET LOCAL app.current_user_id = '<uuid>'` is called at the start of every authenticated database session
- **Service layer**: All service methods include `user_id` in query predicates (defence-in-depth)
- **TenantValidator**: Explicit ownership checks as a tertiary safeguard

### API Protection

- **Rate limiting**: Redis-backed sliding-window counters
  - `/api/auth/login`: 5 requests per 60 seconds
  - `/api/auth/register`: 3 requests per 5 minutes
  - Default: 100 requests per 60 seconds
  - Exceeding limits returns `429 Too Many Requests` with `Retry-After` header
- **CSRF protection**: One-time Redis tokens (`X-CSRF-Token` header)
  - Required for all POST/PATCH/DELETE requests on authenticated endpoints
  - Tokens are consumed on first use (cannot be replayed)
  - Token lifetime: 1 hour
  - Public endpoints (`/login`, `/register`, `/health`) are exempt

### Audit

- All POST, PATCH, and DELETE requests by authenticated users are logged to `audit_logs`
- The table is append-only — no delete or update operations are permitted by application code
- Each entry records: `user_id`, `action`, `resource_type`, `resource_id`, `ip_address`, `user_agent`, `created_at`
- Audit logs are accessible via `GET /api/audit/me` by the owning user

---

## Known Limitations

- **No mutual TLS**: API-to-database communication uses password authentication, not mTLS. Ensure the database is not exposed to the public internet.
- **JWT secret rotation**: The current implementation does not support graceful rotation of the JWT signing secret. All tokens are invalidated immediately if `SECRET_KEY` changes.
- **Refresh token revocation**: Refresh tokens are stateless JWTs. There is currently no server-side revocation list; tokens remain valid until expiry even after logout.
- **Rate limits reset on restart**: Redis keys are lost if Redis restarts without persistence configured. Enable `appendonly yes` in `redis.conf` for production.
- **CSRF bypass in development**: When Redis is unavailable the CSRF middleware falls back to allowing requests. This fallback should not be relied upon in production.
- **No account lockout**: After repeated failed logins the rate limiter slows attacks but does not permanently lock accounts.

---

## Security Contact

To report a vulnerability, please send a private email to:

**security@swingtrade.local** (replace with your actual security contact)

Please include:
1. A description of the vulnerability
2. Steps to reproduce
3. Potential impact

We aim to acknowledge reports within 48 hours and provide a resolution timeline within 7 days.

Do **not** open a public GitHub issue for security vulnerabilities.
