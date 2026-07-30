# Barebonde - Project README

Regnskaps- og administrasjonsplattform for norske bønder og små landbruksvirksomheter.

## 🎯 Vision

Én digital løsning for alt: Regnskap, avtaler, dokumenter, frister, og kommunikasjon med offentlige tjenester.

Målet er å gi bønder tilbake tiden til det de er gode på — å drive gården — og bort fra skrivebord og papirer.

## 🌱 Status

**Phase 1: Foundation** — Under implementasjon

- ✅ Produktarkitektur definert
- ✅ Teknisk stack valgt
- ✅ Prosjektstruktur opprettet
- 🟡 Authentication (ID-porten) — under arbeid
- ⚪ Regnskap — neste

## 🚀 Quick Start

See [IMPLEMENTATION.md](./IMPLEMENTATION.md) for detailed setup guide.

```bash
# Backend
cd backend
python -m venv venv
venv\Scripts\activate  # Windows
pip install -r requirements.txt
python -m uvicorn main:app --reload

# Frontend
cd frontend
npm install
npm run dev
```

Backend: http://localhost:8000  
Frontend: http://localhost:3000

## 📋 Architecture

### Stack
- **Backend:** Python + FastAPI
- **Frontend:** Next.js (React + TypeScript)
- **Database:** PostgreSQL
- **Hosting:** Azure (Nord-Europa)
- **Auth:** ID-porten + JWT

### Domain Model

```
Farm (Gård)
├─ Organization (AS/ENK via BRREG)
├─ Users (multi-tenant, role-based)
├─ Transactions (Income/Expense)
├─ Documents (Contracts, Invoices, Permits)
├─ Deadlines (Tax, Agricultural, Legal)
└─ Properties (Eiendom via Gårdskart)
```

## 📁 Project Structure

```
barebonde/
├── backend/                 # FastAPI application
│   ├── app/
│   │   ├── api/            # API routes
│   │   ├── db/             # Database models
│   │   ├── services/       # Business logic
│   │   ├── schemas/        # Pydantic models
│   │   └── core/           # Config, security
│   ├── tests/              # Unit tests
│   ├── main.py             # App entry
│   └── requirements.txt
│
├── frontend/                # Next.js application
│   ├── app/                 # Pages & routes
│   ├── components/          # Reusable components
│   ├── styles/              # Global styles
│   └── package.json
│
├── docs/
│   ├── architecture/        # ADRs, diagrams
│   ├── database/            # Schema, migrations
│   ├── product-vision.md    # Product strategy
│   ├── inspiration.md       # Reference solutions
│   └── IMPLEMENTATION.md    # Setup guide
│
└── backlog/
    └── epics.md             # Feature backlog
```

## 🔐 Security

- **Authentication:** OAuth2 with Norwegian ID-porten
- **Authorization:** JWT tokens + role-based access
- **Data:** Row-level isolation per farm
- **Audit:** All sensitive operations logged
- **TLS:** HTTPS required in production

## 📈 Phases

| Phase | Timeline | Focus | Status |
|-------|----------|-------|--------|
| **Phase 1** | Weeks 1-2 | Auth + Multi-tenant | 🟡 In Progress |
| **Phase 2** | Weeks 3-8 | Regnskap + Dokumenter + Frister | ⚪ To Do |
| **Phase 3** | Weeks 9-10 | Peppol + eSignering + Offentlige APIer | ⚪ To Do |
| **Phase 4** | Weeks 11-12 | Maskin + Planlegging (post-MVP) | ⚪ To Do |

## 🎯 MVP Scope

**Included:**
- User authentication via ID-porten
- Farm setup and multi-user management
- Income/Expense tracking
- Document upload and versioning
- Contract management with eSignering
- Deadline tracking and notifications

**Not in MVP:**
- Complex accounting features
- Offline functionality
- Mobile apps
- Advanced reporting

## 📚 Documentation

- [Architecture Decision Records](./docs/architecture/adr.md)
- [Database Schema](./docs/database/schema.sql)
- [Product Vision](./docs/product-vision.md)
- [Implementation Guide](./docs/IMPLEMENTATION.md)
- [API Documentation](http://localhost:8000/docs) (when running)

## 🔗 Integrations (Roadmap)

1. **ID-porten** — Authentication ✅ In Phase 1
2. **BRREG** — Organization data — Phase 1
3. **eSignering** — Digital signatures — Phase 2
4. **Peppol/ELMA** — E-invoices — Phase 3
5. **Gårdskart** — Property mapping — Phase 2
6. **Offentlige registre** — Tax, subsidies, permits — Phase 3

## 👥 Contributing

Team: Solo/1-2 developers  
Timeline: 3 months to MVP

## ⚠️ Known Issues

- [ ] ID-porten integration needs real credentials
- [ ] Multi-tenant middleware not yet implemented
- [ ] Frontend token storage (localStorage) should be httpOnly cookies
- [ ] No rate limiting on auth endpoints

## 📞 Support

Contact: Not yet - team internal project

## 📄 License

Proprietary - Barebonde ASA

---

**Last Updated:** July 30, 2026  
**Next Review:** After Phase 1 complete
