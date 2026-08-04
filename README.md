# Barebonde

Barebonde er en modulær plattform for norske gårdsbruk og landbruksforetak. Løsningen utvikles rundt gårdsoversikt, regnskap og bilag, dokumenter, frister, ressurser og drift.

## Dagens løsning

- `frontend/`: Next.js 14 med TypeScript og statisk eksport til Azure Static Web Apps.
- `backend/`: FastAPI pakket som én Azure Functions `AsgiFunctionApp` i `function_app.py`.
- Data: Azure Cosmos DB (NoSQL) for domeneobjekter og Azure Blob Storage for dokumenter.
- Integrasjoner: BRREG-oppslag, Plunk for transaksjonell e-post og Google Identity Services i dagens onboarding.
- Leveranse: eksisterende GitHub Actions-workflows bygger og publiserer frontend og Function App.

Cloudflare- og Azure-konfigurasjon håndteres manuelt i MVP-en. Det er ikke planlagt IaC i denne fasen.

## Sikkerhetsstatus

Dagens Google- og e-postflyt er en overgangsløsning og er **ikke produksjonsklar autentisering eller autorisering**. Den må ikke behandles som sikker identitets-, abonnements- eller rettighetskilde, og klientlagring er ikke en erstatning for serverstyrte sesjoner.

Før videre Identity-arbeid skal eksisterende Cosmos-containere valideres med et eksplisitt bootstrap-steg. Deretter er den planlagte retningen serverstyrte sesjoner i Cosmos, `HttpOnly`-cookie, CSRF-beskyttelse og en autoritativ `FarmUser`-medlemskapsmodell. Ory/Kratos, Better Auth, SQLAlchemy og PostgreSQL er ikke del av løsningen.

Et eventuelt tidligere Ory-prosjekt må slettes eller deaktiveres manuelt i Ory-konsollen; repositoryet kan ikke gjøre dette.

## Lokal utvikling

```bash
# Backend
cd backend
python -m venv venv
venv\Scripts\activate  # Windows
pip install -r requirements.txt
copy local.settings.example.json local.settings.json
python -m uvicorn main:app --reload

# Frontend
cd frontend
npm ci
npm run dev
```

Fyll kun lokale verdier i `backend/local.settings.json`; filen er ignorert av Git. Se `backend/.env.example` for miljøvariabler. Testene bruker mocks og skal ikke koble til Azure-ressurser.

## Kvalitetskontroller

```bash
# Backend
cd backend
python -m pytest

# Frontend
cd frontend
npm run lint
npx tsc --noEmit
npm run build
```

## Repositorystuktur

```text
backend/                 FastAPI og Azure Functions
  app/api/routes/        Health-, auth-, gårds- og regnskapsruter
  app/db/                Cosmos-klient og dokumentmodeller
  app/services/          BRREG, Blob Storage, OCR og regnskapskatalog
  tests/                 Isolerte backend-tester
frontend/                Next.js-applikasjon
backlog/                 Produktbacklog
docs/architecture/       Arkitekturbeslutninger
.github/workflows/       Bygg og deploy
```

## Dokumentasjon

- [Arkitekturbeslutninger](./docs/architecture/adr.md)
- [Produktbacklog](./backlog/epics.md)
- [Google-oppsett](./docs/GOOGLE_OAUTH_SETUP.md)
- [Statusrapport](./STATUS_REPORT.md)
- [Sjekkliste](./CHECKLIST.md)

## Neste planlagte fase

`Eksplisitt Cosmos bootstrap og validering av eksisterende containere`.
