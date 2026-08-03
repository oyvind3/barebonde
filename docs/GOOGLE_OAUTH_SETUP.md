# Google OAuth 2.0 Integration Guide

Complete integration of Google Sign-In for your Barebonde platform (Next.js frontend + Python FastAPI backend).

## Overview

This guide covers:
- ✅ Environment variable setup (secure credential management)
- ✅ Frontend integration with Google Identity Services
- ✅ Backend token verification with Python
- ✅ Secure server-side validation
- ✅ User creation/update in Cosmos DB

## Security Architecture

```
┌─────────────┐
│   Browser   │
│ (Frontend)  │
└──────┬──────┘
       │
       │ 1. Google Identity Services script
       │ 2. User clicks "Sign in with Google"
       │ 3. Google returns JWT token
       │ 4. Send token to backend
       │
       ▼
┌─────────────────────────┐
│   Python FastAPI        │
│   Backend               │
│ (/api/auth/google)      │
└──────┬──────────────────┘
       │
       │ 5. Verify JWT signature with google-auth
       │ 6. Check token audience (CLIENT_ID)
       │ 7. Extract user info (email, name, sub)
       │ 8. Create/update user in Cosmos DB
       │ 9. Return safe user object
       │
       ▼
┌─────────────┐
│  Cosmos DB  │
│  (Storage)  │
└─────────────┘
```

## Step 1: Google Cloud Setup

### 1.1 Create OAuth 2.0 Credentials

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing one
3. Enable Google+ API
4. Go to **Credentials** → **Create Credentials** → **OAuth 2.0 Client ID**
5. Choose **Web application** type
6. Add authorized redirect URIs:
   - `http://localhost:3000` (local development)
   - `http://localhost:8000` (local backend)
   - `https://your-production-domain.com` (production)

7. Copy the **Client ID** and **Client Secret**

## Step 2: Environment Variable Setup

### 2.1 Backend (.env)

Create or update `backend/.env`:

```env
# Google OAuth Credentials (Server-side only)
GOOGLE_CLIENT_ID=your_client_id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your_client_secret_here

# Make sure these are never exposed to frontend
# GOOGLE_CLIENT_SECRET should only be used server-side
```

### 2.2 Frontend (.env.local)

Create or update `frontend/.env.local`:

```env
# Only expose the CLIENT_ID (safe to be public)
# NEVER expose CLIENT_SECRET to frontend
NEXT_PUBLIC_GOOGLE_CLIENT_ID=your_client_id.apps.googleusercontent.com

# Also needed for backend communication
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### 2.3 Environment Variable Security Rules

| Variable | Frontend | Backend | Secret? |
|----------|----------|---------|---------|
| `GOOGLE_CLIENT_ID` | ✅ `NEXT_PUBLIC_` prefix | ✅ from `.env` | No |
| `GOOGLE_CLIENT_SECRET` | ❌ **NEVER** | ✅ from `.env` only | **YES** |

**Why?**
- `CLIENT_ID` is public (anyone can see it in browser DevTools)
- `CLIENT_SECRET` must stay server-side only
- Frontend never needs the secret for token verification
- Backend does the token verification with the secret

## Step 3: Backend Implementation

### 3.1 Install Dependencies

The integration requires the `google-auth` library. Add to `requirements.txt`:

```
google-auth==2.27.0
```

Then run:
```bash
pip install -r requirements.txt
```

### 3.2 Google Auth Endpoint

The backend endpoint is located at: `backend/app/api/routes/auth.py`

**Endpoint:** `POST /api/auth/google`

**Request:**
```json
{
  "token": "eyJhbGciOiJSUzI1NiIsImtpZCI6IjEyMzQ1Njc4OTAiLCJ0eXAiOiJKV1QifQ..."
}
```

**Success Response (200):**
```json
{
  "user_id": "1234567890",
  "email": "ola@norskbonde.no",
  "first_name": "Ola",
  "picture": "https://lh3.googleusercontent.com/...",
  "message": "Innlogget med Google"
}
```

**Error Responses:**
- `400` - Missing or empty token
- `401` - Invalid or expired token
- `500` - Server error

### 3.3 How Token Verification Works

```python
# 1. Token arrives from frontend (JWT)
token = "eyJhbGciOiJSUzI1NiIsImtpZCI6IjEyMzQ1Njc4OTAiLCJ0eXAiOiJKV1QifQ..."

# 2. Backend verifies signature with Google's public keys
payload = id_token.verify_oauth2_token(
    token,
    request,
    audience=GOOGLE_CLIENT_ID  # Ensures token is for our app
)

# 3. Extract verified user info
user_id = payload.get("sub")        # Google's unique user ID
email = payload.get("email")        # User's email
name = payload.get("name")          # User's full name
picture = payload.get("picture")    # User's profile picture

# 4. Create/update user in Cosmos DB
# 5. Return safe user object
```

## Step 4: Frontend Implementation

### 4.1 Google Login Button Component

The component is located at: `frontend/components/auth/GoogleLoginButton.tsx`

Features:
- ✅ Loads Google Identity Services script
- ✅ Renders official Google button
- ✅ Sends JWT token to backend
- ✅ Handles errors gracefully
- ✅ Redirects to dashboard on success
- ✅ No sensitive data exposed

### 4.2 Using the Component

```tsx
import { GoogleLoginButton } from '@/components/auth/GoogleLoginButton'

export default function LoginPage() {
  return (
    <GoogleLoginButton
      onSuccess={(user) => {
        console.log('User logged in:', user)
      }}
      onError={(error) => {
        console.error('Login failed:', error)
      }}
      className="mb-6"
    />
  )
}
```

### 4.3 Frontend Flow

```
1. Component loads Google Identity Services script
   └─ https://accounts.google.com/gsi/client

2. Google button rendered in DOM
   └─ User sees official Google Sign-In button

3. User clicks button
   └─ Google shows popup/prompt

4. User signs in with Google account
   └─ Google returns JWT token

5. Token sent to backend: POST /api/auth/google
   └─ { token: "JWT..." }

6. Backend verifies token and returns user info
   └─ { user_id, email, first_name, picture }

7. Store user data in localStorage (or state manager)
   └─ Redirect to /dashboard
```

## Step 5: Database Schema Updates

The `User` model in `backend/app/db/cosmos_models.py` should support Google auth fields:

```python
class User(BaseModel):
    id: str
    email: str
    first_name: str
    last_name: str
    google_id: str = None  # Google's unique user ID
    picture: str = None    # Google profile picture URL
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
```

## Step 6: Testing Locally

### 6.1 Start Backend

```bash
cd backend
python -m uvicorn app.main:app --reload --port 8000
```

Verify running:
```bash
curl http://localhost:8000/health
```

### 6.2 Start Frontend

```bash
cd frontend
npm run dev
```

Open: `http://localhost:3000/login`

### 6.3 Test Google Sign-In

1. Click "Sign in with Google" button
2. Sign in with your Google account
3. Should see:
   - Token sent to `/api/auth/google`
   - Backend logs: `Google auth successful for user: ...`
   - Redirect to `/dashboard`

### 6.4 Debug

Check browser console for:
- Google script loading errors
- Token verification errors
- Network requests to backend

Check backend logs:
```bash
# Look for "Google auth" messages
tail -f backend.log
```

## Step 7: Production Deployment

### 7.1 Environment Variables

Set in your hosting platform (Azure App Service):

**Backend Settings:**
```
GOOGLE_CLIENT_ID=your_prod_client_id
GOOGLE_CLIENT_SECRET=your_prod_secret (SECURE)
```

**Frontend Settings:**
```
NEXT_PUBLIC_GOOGLE_CLIENT_ID=your_prod_client_id
NEXT_PUBLIC_API_URL=https://your-api-domain.com
```

### 7.2 Google Cloud Setup

Add production redirect URIs:
- `https://your-frontend-domain.com`
- `https://your-api-domain.com`

### 7.3 Security Checklist

- ✅ `GOOGLE_CLIENT_SECRET` is NOT in version control
- ✅ `GOOGLE_CLIENT_SECRET` is set only server-side
- ✅ Environment variables are different per environment
- ✅ HTTPS enforced in production
- ✅ CORS configured correctly
- ✅ Token expiration handled (tokens expire after 1 hour)

## Troubleshooting

### "Google Client ID not configured"

**Problem:** Frontend can't find `NEXT_PUBLIC_GOOGLE_CLIENT_ID`

**Solution:**
1. Verify `.env.local` has the variable
2. Restart dev server: `npm run dev`
3. Check browser console

### "Audience mismatch"

**Problem:** Backend says "audience mismatch"

**Solution:**
1. Verify `GOOGLE_CLIENT_ID` matches in both frontend and backend
2. Make sure redirect URIs are registered in Google Cloud Console

### "Token expired"

**Problem:** "Invalid token" error

**Solution:**
1. Google tokens expire after 1 hour
2. User must re-authenticate
3. Implement token refresh on backend if needed

### "Cosmos DB error"

**Problem:** User created but DB fails silently

**Solution:**
1. Check Cosmos DB connection string
2. Verify database exists
3. Authentication still works even if DB fails

## Next Steps

- [ ] Store JWT token in HTTP-only cookie for persistent sessions
- [ ] Implement logout functionality
- [ ] Add "Link Google Account" to user settings
- [ ] Setup token refresh for long sessions
- [ ] Add rate limiting on `/api/auth/google` endpoint
- [ ] Log authentication events to audit trail
- [ ] Test with multiple Google accounts
- [ ] Setup MFA (if needed)

## API Reference

### POST /api/auth/google

Verify Google OAuth token and authenticate user.

**Request:**
```
POST /api/auth/google
Content-Type: application/json

{
  "token": "eyJhbGciOiJSUzI1NiIsImtpZCI6IjEyMzQ1Njc4OTAiLCJ0eXAiOiJKV1QifQ..."
}
```

**Success (200):**
```json
{
  "user_id": "104932523859237643891",
  "email": "ola.nordmann@gmail.com",
  "first_name": "Ola",
  "picture": "https://lh3.googleusercontent.com/a-/...",
  "message": "Innlogget med Google"
}
```

**Client Error (400):**
```json
{
  "detail": "Token er påkrevd"
}
```

**Auth Error (401):**
```json
{
  "detail": "Ugyldig Google-token: ..."
}
```

**Server Error (500):**
```json
{
  "detail": "Google autentisering feilet: ..."
}
```

## Files Modified/Created

- ✅ `backend/requirements.txt` - Added google-auth
- ✅ `backend/app/api/routes/auth.py` - Added `/api/auth/google` endpoint
- ✅ `backend/.env.example` - Added Google credentials template
- ✅ `frontend/components/auth/GoogleLoginButton.tsx` - Created login component
- ✅ `frontend/app/login/page.tsx` - Integrated Google button
- ✅ `frontend/.env.example` - Added Google Client ID template

## References

- [Google Identity Services Documentation](https://developers.google.com/identity/gsi/web)
- [google-auth-library-python](https://github.com/googleapis/google-auth-library-python)
- [JWT Token Structure](https://jwt.io/)
- [OAuth 2.0 Best Practices](https://datatracker.ietf.org/doc/html/draft-ietf-oauth-security-topics)

---

**Last Updated:** August 2026
**Maintained by:** Barebonde Team
