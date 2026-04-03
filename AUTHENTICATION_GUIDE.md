# Authentication System Guide

Complete guide for using the JWT authentication system in Swing Trade Platform API.

## Quick Start

### 1. Register a New User

```bash
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "SecurePass123!",
    "first_name": "John",
    "last_name": "Doe"
  }'
```

**Response:**
```json
{
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "email": "user@example.com",
  "message": "User registered successfully. Please check your email to verify your account."
}
```

### 2. Verify Email

In development, the verification URL is printed to the console. Copy it and visit:

```
http://localhost:8000/api/auth/verify/your_token_here
```

Or use curl:

```bash
curl -X GET http://localhost:8000/api/auth/verify/your_token_here
```

**Response:**
```json
{
  "message": "Email verified successfully",
  "user_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

### 3. Login

```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "SecurePass123!"
  }'
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

### 4. Access Protected Endpoints

Use the access token in the Authorization header:

```bash
curl -H "Authorization: Bearer {access_token}" \
  http://localhost:8000/api/users/me
```

**Response:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "email": "user@example.com",
  "first_name": "John",
  "last_name": "Doe",
  "timezone": "UTC",
  "risk_limit_pct": 2.0,
  "is_email_verified": true,
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T10:30:00Z"
}
```

### 5. Refresh Access Token

When your access token expires (after 1 hour), use the refresh token:

```bash
curl -X POST http://localhost:8000/api/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{
    "refresh_token": "{refresh_token}"
  }'
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

## Password Requirements

Passwords must meet all of the following criteria:

- **Minimum Length:** 8 characters
- **Uppercase Letter:** At least 1 (A-Z)
- **Lowercase Letter:** At least 1 (a-z)
- **Digit:** At least 1 (0-9)
- **Special Character:** At least 1 (!@#$%^&*)

### Examples

✓ Valid: `SecurePass123!`, `MyP@ssw0rd`, `Test$123abc`
✗ Invalid: `password123!` (no uppercase), `PASSWORD123!` (no lowercase), `Secure!` (no digit), `Secure123` (no special char)

## Token Details

### Access Token
- **Expiry:** 1 hour
- **Purpose:** Authenticate API requests
- **Header:** `Authorization: Bearer {token}`
- **Refresh:** Use refresh token when expired

### Refresh Token
- **Expiry:** 7 days
- **Purpose:** Obtain new access token
- **Usage:** POST to `/api/auth/refresh`
- **Security:** Should be stored securely (HttpOnly cookie in production)

## API Endpoints

### POST /api/auth/register
Register a new user account.

**Request:**
```json
{
  "email": "user@example.com",
  "password": "SecurePass123!",
  "first_name": "John",
  "last_name": "Doe"
}
```

**Status Codes:**
- `201` Created - Registration successful
- `400` Bad Request - Password too weak
- `409` Conflict - Email already registered
- `422` Unprocessable Entity - Invalid data format

---

### GET /api/auth/verify/{token}
Verify email address.

**URL Parameters:**
- `token` (string) - Verification token from email

**Status Codes:**
- `200` OK - Email verified
- `400` Bad Request - Invalid or expired token

---

### POST /api/auth/login
Authenticate user and receive tokens.

**Request:**
```json
{
  "email": "user@example.com",
  "password": "SecurePass123!"
}
```

**Status Codes:**
- `200` OK - Login successful
- `401` Unauthorized - Invalid credentials or email not verified
- `422` Unprocessable Entity - Invalid data format

---

### POST /api/auth/refresh
Obtain new access token using refresh token.

**Request:**
```json
{
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Status Codes:**
- `200` OK - Token refreshed
- `401` Unauthorized - Invalid or expired refresh token
- `422` Unprocessable Entity - Invalid data format

---

### GET /api/users/me
Get current user profile (requires authentication).

**Headers:**
```
Authorization: Bearer {access_token}
```

**Status Codes:**
- `200` OK - User data returned
- `401` Unauthorized - Missing or invalid token

## Environment Variables

Configure authentication behavior via environment variables:

```bash
# JWT Settings
SECRET_KEY=your-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
REFRESH_TOKEN_EXPIRE_DAYS=7

# Email Settings (Development)
SMTP_HOST=''  # Leave empty for console output
SMTP_PORT=587
SMTP_USER=''
SMTP_PASSWORD=''
SMTP_FROM_EMAIL='noreply@swingtrade.local'
SMTP_FROM_NAME='Swing Trade Platform'

# Environment
ENVIRONMENT=development  # development or production
```

## Common Error Messages

### "Email already registered"
- **Status:** 409 Conflict
- **Cause:** Email address is already in use
- **Solution:** Use a different email or login if you already have an account

### "Please verify your email before logging in"
- **Status:** 401 Unauthorized
- **Cause:** User hasn't verified their email yet
- **Solution:** Check email for verification link and click it

### "Invalid email or password"
- **Status:** 401 Unauthorized
- **Cause:** Email doesn't exist or password is wrong
- **Solution:** Double-check credentials

### "Invalid or expired token"
- **Status:** 401 Unauthorized
- **Cause:** Token is invalid, expired, or tampered with
- **Solution:** Login again to get new tokens

### "Password must be at least 8 characters"
- **Status:** 400 Bad Request
- **Cause:** Password doesn't meet minimum length requirement
- **Solution:** Use a longer password with mixed character types

## Security Best Practices

1. **Never commit tokens** to version control
2. **Store tokens securely:** Use HttpOnly cookies in browsers
3. **Use HTTPS in production** - Never transmit tokens over HTTP
4. **Rotate tokens:** Implement logout and token blacklist in future
5. **Protect refresh tokens:** Store separately from access tokens
6. **Monitor login attempts:** Implement rate limiting (coming in P1-5)
7. **Never log passwords or tokens** - Check application logs

## Testing

Run the complete test suite:

```bash
cd backend
pytest tests/test_auth.py -v
```

Run with coverage report:

```bash
pytest tests/test_auth.py --cov=app.services --cov=app.api --cov=app.core --cov-report=html
```

Open `htmlcov/index.html` in a browser to view coverage details.

## Development Mode Features

- Email verification links printed to console
- No SMTP configuration required
- SQLite in-memory database for tests
- Debug logging enabled
- OpenAPI documentation at `/docs`

## Production Checklist

- [ ] Set strong `SECRET_KEY` (minimum 32 characters)
- [ ] Configure `ENVIRONMENT=production`
- [ ] Set up SMTP server credentials
- [ ] Enable HTTPS on all endpoints
- [ ] Implement rate limiting on auth endpoints
- [ ] Set up token blacklist/logout mechanism
- [ ] Configure CORS properly
- [ ] Set up logging and monitoring
- [ ] Backup user data regularly
- [ ] Implement password reset flow
- [ ] Add 2FA support (optional but recommended)

## Troubleshooting

### Tokens not working
1. Check token hasn't expired (access: 1 hour, refresh: 7 days)
2. Verify Authorization header format: `Bearer {token}`
3. Check secret key matches across requests
4. Look for JWT decode errors in logs

### Email verification not working
1. In development, check console logs for verification URL
2. In production, check SMTP settings
3. Verify email is not in spam folder
4. Check token hasn't expired (24 hours by default)

### Registration fails with 422
1. Check all required fields are present
2. Verify email format is valid (user@domain.com)
3. Ensure password meets all requirements
4. Check for special characters in names

## Support

For issues or questions:
1. Check this guide first
2. Review test cases in `tests/test_auth.py`
3. Check application logs for error details
4. Verify API documentation at `/docs` endpoint
