# User Account Settings API Documentation

## Overview

The User Account Settings API allows authenticated users to manage their account profile, including personal information, timezone, risk limits, password, and email address.

## Base URL

```
http://localhost:8000/api/users
```

## Authentication

All endpoints require authentication via JWT Bearer token. Include the token in the Authorization header:

```
Authorization: Bearer <access_token>
```

## Endpoints

### 1. Get Current User Profile

Retrieve the authenticated user's profile information.

**Endpoint:** `GET /me`

**Headers:**
- `Authorization: Bearer <access_token>` (required)

**Response:** `200 OK`

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

**Error Responses:**
- `401 Unauthorized` - Missing or invalid token

**Example:**
```bash
curl -X GET http://localhost:8000/api/users/me \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

---

### 2. Update User Settings

Update user profile settings (name, timezone, risk limit).

**Endpoint:** `PATCH /me`

**Headers:**
- `Authorization: Bearer <access_token>` (required)
- `Content-Type: application/json`

**Request Body:**
```json
{
  "first_name": "John",              // optional, max 100 chars
  "last_name": "Smith",              // optional, max 100 chars
  "timezone": "America/New_York",    // optional, must be valid IANA timezone
  "risk_limit_pct": 5.5              // optional, 0.1-100.0
}
```

**Response:** `200 OK`
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "email": "user@example.com",
  "first_name": "John",
  "last_name": "Smith",
  "timezone": "America/New_York",
  "risk_limit_pct": 5.5,
  "is_email_verified": true,
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T10:35:00Z"
}
```

**Error Responses:**
- `400 Bad Request` - Invalid timezone or risk limit
- `401 Unauthorized` - Missing or invalid token
- `422 Unprocessable Entity` - Validation error

**Validation Rules:**
- `first_name`: 1-100 characters
- `last_name`: 1-100 characters
- `timezone`: Valid IANA timezone (e.g., "America/New_York", "Europe/London", "Asia/Tokyo")
- `risk_limit_pct`: Float between 0.1 and 100.0

**Example:**
```bash
curl -X PATCH http://localhost:8000/api/users/me \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
  -H "Content-Type: application/json" \
  -d '{
    "timezone": "America/New_York",
    "risk_limit_pct": 5.5
  }'
```

---

### 3. Change Password

Change the user's password. Requires confirmation with current password.

**Endpoint:** `PATCH /me/password`

**Headers:**
- `Authorization: Bearer <access_token>` (required)
- `Content-Type: application/json`

**Request Body:**
```json
{
  "old_password": "SecurePass123!",
  "new_password": "NewSecurePass456!"
}
```

**Response:** `200 OK`
```json
{
  "success": true,
  "message": "Password changed successfully"
}
```

**Error Responses:**
- `400 Bad Request` - Incorrect old password or weak new password
- `401 Unauthorized` - Missing or invalid token
- `422 Unprocessable Entity` - Validation error

**Password Requirements:**
- Minimum 8 characters
- At least 1 uppercase letter (A-Z)
- At least 1 lowercase letter (a-z)
- At least 1 digit (0-9)
- At least 1 special character (!@#$%^&*()_+-=[]{}:;'",.<>?/\|`~)

**Example:**
```bash
curl -X PATCH http://localhost:8000/api/users/me/password \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
  -H "Content-Type: application/json" \
  -d '{
    "old_password": "SecurePass123!",
    "new_password": "NewSecurePass456!"
  }'
```

---

### 4. Change Email Address

Change the user's email address. Requires password confirmation and email re-verification.

**Endpoint:** `PATCH /me/email`

**Headers:**
- `Authorization: Bearer <access_token>` (required)
- `Content-Type: application/json`

**Request Body:**
```json
{
  "new_email": "newemail@example.com",
  "password": "SecurePass123!"
}
```

**Response:** `200 OK`
```json
{
  "success": true,
  "message": "Email change initiated. Please verify your new email address."
}
```

**Error Responses:**
- `400 Bad Request` - Incorrect password or email already registered
- `401 Unauthorized` - Missing or invalid token
- `422 Unprocessable Entity` - Invalid email format

**Notes:**
- The new email must be unique and not already registered
- After changing email, the account email is marked as unverified
- A verification email is sent to the new address
- User must verify the new email before the change is fully active
- Email addresses are stored in lowercase

**Example:**
```bash
curl -X PATCH http://localhost:8000/api/users/me/email \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
  -H "Content-Type: application/json" \
  -d '{
    "new_email": "newemail@example.com",
    "password": "SecurePass123!"
  }'
```

---

## Common Use Cases

### Update Profile Information

```bash
curl -X PATCH http://localhost:8000/api/users/me \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "first_name": "Jane",
    "last_name": "Doe",
    "timezone": "Europe/London"
  }'
```

### Change Risk Limit

```bash
curl -X PATCH http://localhost:8000/api/users/me \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "risk_limit_pct": 3.5
  }'
```

### Update All Settings At Once

```bash
curl -X PATCH http://localhost:8000/api/users/me \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "first_name": "John",
    "last_name": "Smith",
    "timezone": "America/Los_Angeles",
    "risk_limit_pct": 10.0
  }'
```

### Change Password

```bash
curl -X PATCH http://localhost:8000/api/users/me/password \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "old_password": "OldPass123!",
    "new_password": "NewPass456!"
  }'
```

### Change Email

```bash
curl -X PATCH http://localhost:8000/api/users/me/email \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "new_email": "newemail@example.com",
    "password": "CurrentPass123!"
  }'
```

---

## Valid Timezones

The API accepts any valid IANA timezone. Common examples:

**North America:**
- `America/New_York` (Eastern)
- `America/Chicago` (Central)
- `America/Denver` (Mountain)
- `America/Los_Angeles` (Pacific)

**Europe:**
- `Europe/London` (GMT/BST)
- `Europe/Paris` (CET/CEST)
- `Europe/Berlin` (CET/CEST)
- `Europe/Amsterdam` (CET/CEST)

**Asia:**
- `Asia/Tokyo` (JST)
- `Asia/Hong_Kong` (HKT)
- `Asia/Singapore` (SGT)
- `Asia/Dubai` (GST)
- `Asia/Kolkata` (IST)

**Australia:**
- `Australia/Sydney` (AEDT/AEST)
- `Australia/Melbourne` (AEDT/AEST)
- `Australia/Brisbane` (AEST)

**UTC:**
- `UTC` (Coordinated Universal Time)

---

## Error Handling

All error responses follow this format:

```json
{
  "detail": "Error message describing what went wrong"
}
```

**Common HTTP Status Codes:**
- `200 OK` - Request successful
- `400 Bad Request` - Validation error or business logic error
- `401 Unauthorized` - Missing or invalid authentication token
- `422 Unprocessable Entity` - Request body validation error (invalid types, out of range, etc.)

---

## Security Considerations

1. **Password Security:**
   - Passwords are hashed using PBKDF2-SHA256
   - Never transmitted in responses
   - Always validate strength requirements
   - Old password must match for password changes

2. **Email Verification:**
   - Email changes require re-verification
   - Verification tokens are cryptographically secure
   - Only verified emails can be used for login

3. **Token-Based Authentication:**
   - Access tokens expire after 1 hour
   - Use refresh tokens to obtain new access tokens
   - Always use HTTPS in production

---

## Testing

### Example Test with cURL

```bash
# 1. Register a user
TOKEN=$(curl -s -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"SecurePass123!"}' \
  | jq -r '.access_token')

# 2. Get current user
curl -X GET http://localhost:8000/api/users/me \
  -H "Authorization: Bearer $TOKEN"

# 3. Update settings
curl -X PATCH http://localhost:8000/api/users/me \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"timezone":"America/New_York"}'

# 4. Change password
curl -X PATCH http://localhost:8000/api/users/me/password \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "old_password":"SecurePass123!",
    "new_password":"NewSecurePass456!"
  }'
```

---

## Implementation Details

### User Service

The `UserService` class handles all user-related business logic:

- `get_user(db, user_id)` - Retrieve user by ID
- `update_user(db, user_id, update_data)` - Update user settings with validation
- `change_password(db, user_id, old_password, new_password)` - Change password with verification
- `change_email(db, user_id, new_email, password)` - Change email with verification

### Database

All user data is persisted in the PostgreSQL database with the following relevant fields:

- `id` - UUID primary key
- `email` - Unique email address (lowercase)
- `password_hash` - PBKDF2-SHA256 hash
- `first_name` - User's first name
- `last_name` - User's last name
- `timezone` - IANA timezone string
- `risk_limit_pct` - Risk limit percentage (Numeric 5,2)
- `is_email_verified` - Boolean verification status
- `email_verification_token` - Temporary verification token
- `created_at` - Account creation timestamp
- `updated_at` - Last update timestamp

### Validation

All inputs are validated:

- **Email:** Must be valid format and unique
- **Timezone:** Must be valid IANA timezone
- **Risk Limit:** Float between 0.1 and 100.0
- **Names:** 1-100 characters
- **Password:** Minimum 8 chars with uppercase, lowercase, digit, special char

---

## Response Examples

### Success Response (200 OK)

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "email": "user@example.com",
  "first_name": "John",
  "last_name": "Doe",
  "timezone": "America/New_York",
  "risk_limit_pct": 5.5,
  "is_email_verified": true,
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T10:35:00Z"
}
```

### Error Response (400 Bad Request)

```json
{
  "detail": "Current password is incorrect"
}
```

### Error Response (422 Unprocessable Entity)

```json
{
  "detail": [
    {
      "loc": ["body", "risk_limit_pct"],
      "msg": "ensure this value is less than or equal to 100",
      "type": "value_error.number.not_le",
      "ctx": {"limit_value": 100.0}
    }
  ]
}
```
