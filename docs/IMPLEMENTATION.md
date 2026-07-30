# Barebonde - Implementation Guide

## Phase 1: Foundation (Auth & Multi-tenant) - Current

### What We Just Set Up

**Backend Structure (Python FastAPI)**
- ✅ Authentication service with ID-porten OAuth2 flow
- ✅ JWT token generation and verification
- ✅ Database models for users, farms, permissions
- ✅ Refresh token management
- ✅ Audit logging foundation

**Frontend Structure (Next.js)**
- ✅ Login page with ID-porten button
- ✅ Dashboard skeleton
- ✅ Tailwind CSS styling
- ✅ Next.js configuration

**Database (PostgreSQL)**
- ✅ Schema for users, farms, farm_users (roles)
- ✅ Refresh token storage
- ✅ Audit logs table
- ✅ Ready for Phase 2 (transactions, documents, deadlines)

---

## Next: Local Development Setup

### 1. Prerequisites
- Python 3.11+
- Node.js 18+
- PostgreSQL 14+
- Git

### 2. Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv

# Activate (Windows)
venv\Scripts\activate

# Or (Mac/Linux)
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Copy and edit .env
cp .env.example .env
# Edit .env with your PostgreSQL credentials and ID-porten settings

# Initialize database
alembic upgrade head

# Run dev server
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Backend should be running at: http://localhost:8000
- Health check: http://localhost:8000/health
- API docs: http://localhost:8000/docs

### 3. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Copy and edit .env
cp .env.example .env.local
# Edit with backend API URL and ID-porten credentials

# Run dev server
npm run dev
```

Frontend should be running at: http://localhost:3000

### 4. Database Setup

```bash
# Create database
createdb barebonde

# Run schema
psql barebonde < docs/database/schema.sql
```

---

## Current Implementation Status

### Epic 1.1: Identitet og Multi-tenant Arkitektur

| Task | Status | Notes |
|------|--------|-------|
| ID-porten OAuth2 integration | 🟡 Partial | Endpoints defined, needs actual ID-porten credentials |
| JWT token generation | ✅ Done | Fully implemented |
| User model | ✅ Done | users table created |
| Farm model | ✅ Done | farms table created |
| Farm-User relationships | ✅ Done | farm_users table with roles |
| Multi-tenant isolation | 🟡 Partial | Middleware not yet implemented |
| Login/Logout endpoints | ✅ Done | Routes defined |
| Refresh token system | ✅ Done | Tables and service ready |

### Epic 1.2: Gårdsetablering og Organisasjonsprofil

| Task | Status | Notes |
|------|--------|-------|
| BRREG API integration | ⚪ TODO | Placeholder only |
| Gårdskart integration | ⚪ TODO | For Phase 2 |
| Farm creation form | ⚪ TODO | Frontend form needed |
| Farm editing | ⚪ TODO | For Phase 2 |

---

## Critical Next Steps (Priority Order)

### Immediate (This Week)
1. **ID-porten Real Integration**
   - Get actual CLIENT_ID and CLIENT_SECRET from Digitaliseringsdirektoratet
   - Implement actual token exchange
   - Test login flow end-to-end
   - **File:** `backend/app/services/auth_service.py`

2. **Multi-tenant Middleware**
   - Add FastAPI middleware to inject farm_id from JWT
   - Verify user has access to requested farm
   - Block unauthorized farm access
   - **Files:** `backend/app/core/security.py` (new)

3. **Frontend Auth Flow**
   - Connect login button to backend `/api/auth/login`
   - Handle callback from ID-porten
   - Store tokens in localStorage (or httpOnly phase 2)
   - Redirect to dashboard on successful login
   - **File:** `frontend/app/page.tsx`

4. **Basic Farm Setup Flow**
   - Form to create farm (name, org.nr)
   - BRREG API lookup for org info
   - Save to database
   - Redirect to dashboard
   - **Files:** `frontend/app/farm/create/page.tsx` (new)

### Next Week
5. **End-to-end Testing**
   - Manual test: Login → Farm creation → Dashboard
   - Test permission system (only owner can see farm)
   - Test multi-user invite flow

6. **Database Migrations**
   - Set up Alembic for schema versioning
   - Document migration strategy
   - **File:** `backend/alembic/` (new)

---

## Technical Debt & Gotchas

| Issue | Severity | Solution |
|-------|----------|----------|
| ID-porten integration is placeholder | 🔴 CRITICAL | Must get real credentials ASAP |
| No rate limiting on auth endpoints | 🟡 HIGH | Add FastAPI middleware + Redis later |
| Passwords not stored (good!), but need more identity checks | 🟡 HIGH | Implement 2FA phase 2 |
| No HTTPS in dev | 🟢 LOW | Works for local dev, fix in staging |
| Frontend stores tokens in localStorage (XSS risk) | 🟡 HIGH | Move to httpOnly cookies phase 2 |
| No CORS configuration | 🟡 HIGH | Update `main.py` with frontend URL |

---

## Testing Strategy

### Unit Tests (Backend)
```bash
cd backend
pytest tests/
```

Start with auth service tests:
- Test JWT token creation/verification
- Test refresh token logic
- Test multi-tenant isolation

### Integration Tests (Phase 2)
- Test full login flow with real ID-porten
- Test farm creation and permission checks
- Test transaction creation and accuracy

### E2E Tests (Phase 2)
- Playwright tests for complete user flows

---

## Deployment Checklist (for later)

- [ ] Azure PostgreSQL database setup
- [ ] Azure Container Registry for Docker images
- [ ] GitHub Actions CI/CD pipeline
- [ ] Environment variable management in Azure
- [ ] SSL certificate setup
- [ ] Rate limiting and DDoS protection
- [ ] Backup strategy for PostgreSQL
- [ ] Monitoring and alerting setup
- [ ] Security audit before launch

---

## Timeline: 3-Month MVP

**Week 1-2 (NOW):** Auth + Farm setup foundation  
**Week 3-4:** Phase 2 - Regnskap (transactions)  
**Week 5-6:** Phase 2 - Dokumenter + Avtaler  
**Week 7-8:** Phase 2 - Frister  
**Week 9-10:** Integration prep (Peppol, eSignering)  
**Week 11-12:** Bug fixes, performance, security hardening  

This assumes ~40 hours/week solo developer.

---

## Questions for Product Team

1. **ID-porten Credentials**: Have you applied for ID-porten client? Can you get CLIENT_ID/SECRET?
2. **BRREG Integration**: Do we need this in MVP? Can we start with manual org.nr entry?
3. **eSignering**: Which provider? (DigiDirs tjeneste, DocuSign, etc?)
4. **Peppol Readiness**: Do we have any test invoices to work with?
5. **Data Residency**: Confirmed Azure Nord-Europa is acceptable for customer data?

---

## Getting Help

- FastAPI docs: https://fastapi.tiangolo.com/
- SQLAlchemy async: https://docs.sqlalchemy.org/
- Next.js docs: https://nextjs.org/docs
- ID-porten: https://www.digdir.no/digital-assistanse/id-porten
- PostgreSQL: https://www.postgresql.org/docs/
