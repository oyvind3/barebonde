# Barebonde - Next Implementation Sprint Plan

**Sprint Goal:** Complete Fase 1.1 (Authentication with ID-porten)  
**Duration:** 1-2 weeks (depending on ID-porten credentials availability)  
**Owner:** Solo developer

---

## 🎯 Primary Objectives

### 1. Real ID-porten Integration (BLOCKER)
**Why:** Everything else depends on auth working  
**Effort:** 4-6 hours  
**Status:** Currently placeholders only

**Tasks:**
- [ ] Obtain ID-porten CLIENT_ID and CLIENT_SECRET from Digitaliseringsdirektoratet
  - Contact: https://www.digdir.no/digital-assistanse/id-porten
  - Need to register application in test environment
- [ ] Implement actual OAuth2 token exchange in `auth_service.py`
  - Replace placeholder in `get_id_porten_login_url()`
  - Implement real `exchange_code_for_token()`
  - Implement real `get_user_info()`
- [ ] Test with curl/Postman before connecting frontend
- [ ] Create integration test for auth flow

**Files to modify:**
- `backend/app/services/auth_service.py` (lines 17-60)
- `backend/app/core/config.py` (add ID-porten URLs)

---

### 2. Multi-tenant Middleware
**Why:** Without this, user A can access user B's data  
**Effort:** 3-4 hours  
**Status:** Not started

**Tasks:**
- [ ] Create security/permissions module
  - `backend/app/core/security.py` (new file)
- [ ] Implement FastAPI dependency for verifying farm access
  - Extract farm_id from JWT token
  - Check if user is in farm_users table
  - Raise 403 if unauthorized
- [ ] Apply middleware to all farm-specific endpoints
  - `/api/farms/{farm_id}/...`
  - Verify user can access this farm
- [ ] Create test for permission verification

**Code template:**
```python
# backend/app/core/security.py
async def verify_farm_access(
    farm_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Verify user has access to farm"""
    stmt = select(FarmUser).where(
        FarmUser.user_id == current_user.id,
        FarmUser.farm_id == farm_id
    )
    farm_user = await db.scalar(stmt)
    if not farm_user:
        raise HTTPException(status_code=403, detail="Unauthorized")
    return farm_user
```

---

### 3. Frontend Auth Flow
**Why:** Users can't login currently  
**Effort:** 4-5 hours  
**Status:** Login button exists, no flow

**Tasks:**
- [ ] Implement ID-porten redirect on login button
  - Call `GET /api/auth/login` → get login_url
  - Redirect to login_url
- [ ] Handle OAuth2 callback
  - Create `app/auth/callback/page.tsx`
  - Extract auth code from URL params
  - Send to `POST /api/auth/callback`
  - Store tokens in localStorage
  - Redirect to dashboard or farm creation
- [ ] Implement useAuth hook
  - Check if user logged in
  - Provide logout function
  - Provide user data
- [ ] Protect dashboard route
  - Redirect to login if not authenticated
- [ ] Test end-to-end login flow

**Files to create/modify:**
- `frontend/app/auth/callback/page.tsx` (new)
- `frontend/lib/auth.ts` (new) - useAuth hook
- `frontend/app/page.tsx` - login button logic
- `frontend/app/dashboard/page.tsx` - add auth check
- `frontend/app/middleware.ts` (new) - route protection

---

### 4. Farm Creation Flow
**Why:** Users can't set up their farm  
**Effort:** 5-6 hours  
**Status:** Not started

**Tasks:**
- [ ] Create farm setup page
  - `frontend/app/farm/setup/page.tsx` (new)
  - Form: Farm name, Org.nr
- [ ] Integrate BRREG API
  - When user enters org.nr, lookup in BRREG
  - Auto-fill: company name, address, industry
  - `backend/app/services/brreg_service.py` (new)
- [ ] Create backend endpoint
  - `POST /api/farms` - create farm
  - Verify org.nr not already in system
  - Assign current user as OWNER
  - Return farm object
- [ ] Handle redirect after creation
  - If first farm: go to dashboard
  - If adding farm: go to farm list
- [ ] Test farm creation

**Files to create/modify:**
- `frontend/app/farm/setup/page.tsx` (new)
- `backend/app/services/brreg_service.py` (new)
- `backend/app/api/routes/farms.py` (new)
- `main.py` - include farms router

---

### 5. Database Migrations (Alembic)
**Why:** Schema changes need versioning  
**Effort:** 2-3 hours  
**Status:** Not started

**Tasks:**
- [ ] Initialize Alembic in backend
  - `alembic init -t async alembic`
- [ ] Configure Alembic for async SQLAlchemy
  - `alembic/env.py` async config
- [ ] Create initial migration
  - `alembic revision --autogenerate -m "initial schema"`
- [ ] Document migration process
  - How to create migrations
  - How to upgrade/downgrade
- [ ] Test migration

---

## 📊 Sprint Breakdown by Day

### Day 1-2: ID-porten Setup
- Get credentials (might be bottleneck)
- Implement real token exchange
- Test with Postman

### Day 3-4: Multi-tenant Middleware
- Build security module
- Apply to auth/farm endpoints
- Write unit tests

### Day 5-6: Frontend Auth
- Build callback page
- Build useAuth hook
- Connect login flow end-to-end
- Manual testing

### Day 7-8: Farm Creation
- Build setup form
- Build BRREG integration
- Build backend endpoint
- Test creation flow

### Day 9: Alembic + Polish
- Setup Alembic
- Create initial migration
- Documentation
- Bug fixes

---

## ⚠️ Critical Blockers

| Blocker | Impact | Solution |
|---------|--------|----------|
| ID-porten credentials | 🔴 CRITICAL - blocks 30% of work | Start application NOW at Digitaliseringsdirektoratet |
| PostgreSQL setup | 🟡 HIGH | Make sure local PostgreSQL is running |
| Node.js/npm version | 🟡 MEDIUM | Ensure Node 18+, npm 9+ |

---

## 🧪 Testing Checklist

After each task, verify:

- [ ] Unit tests pass: `pytest tests/`
- [ ] API returns 200: `curl http://localhost:8000/health`
- [ ] Frontend builds: `npm run build`
- [ ] No TypeScript errors: `npx tsc --noEmit`
- [ ] Manual test: actual login flow in browser

---

## 📋 Definition of Done

**Fase 1.1 is complete when:**
- ✅ User can click "Login" button
- ✅ Redirected to ID-porten
- ✅ After login, returned to app with tokens
- ✅ Tokens stored and persisted
- ✅ User can create a farm
- ✅ Farm owner role assigned
- ✅ User can logout
- ✅ No other user can access their farm
- ✅ All code has 80%+ test coverage

---

## 🚀 Phase Readiness

**Phase 2 can start when:**
- Fase 1.1 is 100% complete
- No critical security issues
- Load test with 10 concurrent users
- Manual testing in staging environment

---

## 📚 Resources

- ID-porten docs: https://www.digdir.no/digital-assistanse/id-porten
- FastAPI deps: https://fastapi.tiangolo.com/tutorial/dependencies/
- JWT with FastAPI: https://fastapi.tiangolo.com/en/latest/advanced/security/jwt/
- BRREG API: https://data.brreg.no/
- Alembic docs: https://alembic.sqlalchemy.org/

---

## Questions / Decisions Needed

1. **ID-porten Test vs Production?**
   - Start with test environment (https://idporten.no-test/)
   - More forgiving rate limits for development

2. **BRREG API Key?**
   - Free public API or need key? (Check docs)

3. **Token storage security:**
   - localStorage for MVP (simple)
   - httpOnly cookies Phase 2 (more secure)

4. **Farm invites workflow:**
   - Phase 1.2 (next sprint) or Phase 2?
   - Currently: owner manually creates users
   - Later: send invite links via email

5. **Testing environment:**
   - Local Docker Compose for PostgreSQL?
   - Or standalone PostgreSQL?
