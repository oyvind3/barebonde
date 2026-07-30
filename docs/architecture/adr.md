# Barebonde - Architecture Decision Log

## ADL-001: Technology Stack

**Status:** DECIDED

**Decision:**
- Backend: Python + FastAPI
- Frontend: Next.js (React + TypeScript)
- Database: PostgreSQL
- Hosting: Azure (Nord-Europa region)
- Authentication: ID-porten OAuth2 → JWT tokens

**Rationale:**
- **FastAPI**: Fast async Python, great for numerical/accounting workloads, excellent ORM support
- **Next.js**: Fullstack React framework, excellent for modern UX + API integration
- **PostgreSQL**: ACID compliance (critical for accounting), good JSON support, proven track record
- **Azure**: Microsoft ecosystem, Norwegian data center, GDPR compliant
- **JWT**: Stateless auth, scales well, works with mobile apps later

**Trade-offs:**
- Python backend requires async programming discipline
- Next.js adds some complexity but provides full-stack flexibility
- PostgreSQL is more complex than NoSQL but necessary for accounting

---

## ADL-002: Multi-tenant Architecture

**Status:** DECIDED

**Decision:**
- Single database, row-level isolation per farm
- JWT tokens include `farm_id` to enforce isolation
- Audit logs for all sensitive operations

**Rationale:**
- Cheaper infrastructure than per-tenant databases
- Simpler deployment and management
- Risk: One SQL injection bug could expose all farms

**Mitigation:**
- SQLAlchemy ORM (parameterized queries)
- Input validation at API layer
- Regular security audits

---

## ADL-003: Authentication Flow

**Status:** DECIDED

**Decision:**
1. Frontend → ID-porten OAuth2 endpoint
2. User logs in with Norwegian ID
3. ID-porten → callback with auth code
4. Backend exchanges code for ID-porten token
5. Backend creates JWT access token + refresh token
6. Frontend stores tokens in localStorage (or httpOnly cookies phase 2)

**Rationale:**
- ID-porten is Norwegian standard (legal requirement)
- JWT allows stateless backend scaling
- Refresh tokens allow long-term access without re-auth

**Security considerations:**
- httpOnly cookies phase 2 (prevent XSS)
- PKCE flow phase 2 (prevent CSRF)
- Token revocation on logout

---

## ADL-004: Accounting Data Model

**Status:** DECIDED

**Design:**
- Simple transaction model (Income/Expense)
- Category-based classification
- No double-entry bookkeeping in MVP (simplify UX)
- Audit trail for all transactions

**Future:**
- Phase 3: Move to proper double-entry when complexity requires

**Rationale:**
- MVP simplicity over accounting purity
- Bønder are not accountants - overcomplicating loses them
- Can migrate to NNRF (Norwegian chart of accounts) later

---

## ADL-005: Document Storage

**Status:** DECIDED

**Decision:**
- Store PDFs/documents in Azure Blob Storage
- Database stores reference + metadata
- No file versioning in MVP

**Rationale:**
- Avoids database bloat
- Azure integrated
- Cheaper than database storage

**Phase 2:** Add version control

---

## ADL-006: Integrations Strategy

**Status:** DECIDED

**Priority order:**
1. ID-porten (auth) - MVP blocker
2. BRREG (org lookup) - UX quality
3. eSignering (contracts) - core feature
4. Peppol/ELMA (invoices) - revenue driver
5. Gårdskart (property mapping) - nice-to-have

**Rationale:**
- Start with highest value / lowest complexity
- Peppol is complex but enables 80/20 value

---

## ADL-007: MVP Scope - What's NOT included

**Status:** DECIDED

**Phase 1 exclusions:**
- ❌ Multi-currency
- ❌ Multiple fiscal years
- ❌ Anleggsmidler (depreciation)
- ❌ Complex permissions (3 roles only)
- ❌ Offline functionality
- ❌ Mobile app

**Rationale:**
- 3-month MVP timeline requires ruthless focus
- 80/20 - these features add 20% value but 80% complexity

---

## Implementation Checklist

- [ ] PostgreSQL schema created
- [ ] Backend FastAPI structure verified
- [ ] ID-porten OAuth2 integration (placeholder)
- [ ] JWT token generation/verification
- [ ] Next.js frontend setup
- [ ] Login flow end-to-end
- [ ] Database migrations (Alembic)
- [ ] Unit tests for auth service
- [ ] Documentation for deployment
