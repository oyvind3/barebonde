# Google OAuth Setup Checklist

## 🔧 Quick Setup (5 minutes)

### 1️⃣ Google Cloud Console Setup

- [ ] Go to [Google Cloud Console](https://console.cloud.google.com/)
- [ ] Create OAuth 2.0 Client ID (Web application)
- [ ] Add redirect URIs:
  - `http://localhost:3000`
  - `http://localhost:8000`
  - `https://your-production-domain.com`
- [ ] Copy **Client ID** and **Client Secret**

### 2️⃣ Backend Environment

Create `backend/.env`:

```
GOOGLE_CLIENT_ID=YOUR_CLIENT_ID_HERE
GOOGLE_CLIENT_SECRET=YOUR_CLIENT_SECRET_HERE
```

### 3️⃣ Frontend Environment

Create `frontend/.env.local`:

```
NEXT_PUBLIC_GOOGLE_CLIENT_ID=YOUR_CLIENT_ID_HERE
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### 4️⃣ Install Dependencies

```bash
cd backend
pip install google-auth==2.27.0
```

### 5️⃣ Test It

Backend:
```bash
cd backend
python -m uvicorn app.main:app --reload
```

Frontend:
```bash
cd frontend
npm run dev
```

Visit: `http://localhost:3000/login`

---

## 🔐 Security Checklist

- [ ] `GOOGLE_CLIENT_SECRET` is in `.env` (never in code)
- [ ] `GOOGLE_CLIENT_SECRET` is never exposed to frontend
- [ ] `.env` files are in `.gitignore`
- [ ] Only `NEXT_PUBLIC_GOOGLE_CLIENT_ID` is in frontend
- [ ] Backend verifies all tokens server-side
- [ ] HTTPS enforced in production

---

## 📁 Files Changed

```
backend/
  ├─ requirements.txt                 ✅ Added google-auth
  ├─ .env.example                     ✅ Google credentials template
  └─ app/api/routes/auth.py           ✅ Added POST /api/auth/google

frontend/
  ├─ .env.example                     ✅ Client ID template
  ├─ app/login/page.tsx               ✅ Integrated GoogleLoginButton
  └─ components/auth/GoogleLoginButton.tsx  ✅ New component

docs/
  ├─ GOOGLE_OAUTH_SETUP.md            ✅ Complete guide
  └─ GOOGLE_OAUTH_QUICK_START.md      ✅ This file
```

---

## 🧪 Test Endpoints

### Backend Verification

```bash
# Check if backend is running
curl http://localhost:8000/health

# Check auth endpoint exists
curl -X POST http://localhost:8000/api/auth/google \
  -H "Content-Type: application/json" \
  -d '{"token": "test"}'
# Should return 401 with "Invalid token" message
```

### Frontend Check

1. Open `http://localhost:3000/login`
2. Look for **"Sign in with Google"** button (official Google styling)
3. Open browser DevTools (F12)
4. Click Google button → sign in with test account
5. Check Network tab:
   - Should see POST to `/api/auth/google`
   - Response should include user info
   - Should redirect to `/dashboard`

---

## 🐛 Common Issues

| Issue | Cause | Fix |
|-------|-------|-----|
| Button doesn't appear | Script not loaded | Check browser console for errors |
| "Audience mismatch" | Client ID mismatch | Verify same ID in frontend + backend |
| "Google Client ID not configured" | Missing env var | Add `NEXT_PUBLIC_GOOGLE_CLIENT_ID` to `.env.local` |
| 401 Unauthorized | Invalid token | Token may be expired, user must re-authenticate |
| CORS error | Backend not accessible | Check `FRONTEND_URL` in backend `.env` |

---

## 📚 Key Files to Review

1. **Backend endpoint**: `backend/app/api/routes/auth.py` → `@router.post("/google")`
2. **Frontend component**: `frontend/components/auth/GoogleLoginButton.tsx`
3. **Login page**: `frontend/app/login/page.tsx`
4. **Full docs**: `docs/GOOGLE_OAUTH_SETUP.md`

---

## 🚀 Next Steps

After basic setup works:

1. Test with multiple Google accounts
2. Setup persistent sessions with HTTP-only cookies
3. Add logout functionality
4. Add rate limiting on auth endpoint
5. Setup audit logging
6. Test in production environment

---

**Need help?** See `docs/GOOGLE_OAUTH_SETUP.md` for detailed troubleshooting.
