# Barebonde

Barebonde er en modulær plattform for norske gårdsbruk og landbruksforetak. Løsningen utvikles rundt gårdsoversikt, regnskap og bilag, dokumenter, frister, ressurser og drift.

**Status**: MVP-fase med identitet, medlemskap, abonnement, tenant-isolasjon og bilagskontroll (opplasting, OCR, korrigering og bokføring) implementert.

## Dagens løsning

- `frontend/`: Next.js 14 med TypeScript og statisk eksport til Azure Static Web Apps.
- `backend/`: FastAPI pakket som én Azure Functions `AsgiFunctionApp` i `function_app.py`.
- Data: Azure Cosmos DB (NoSQL) for domeneobjekter og Azure Blob Storage for dokumenter.
- Integrasjoner: BRREG-oppslag og Plunk for transaksjonell e-post.
- Leveranse: eksisterende GitHub Actions-workflows bygger og publiserer frontend og Function App.

Cloudflare- og Azure-konfigurasjon håndteres manuelt i MVP-en. Det er ikke planlagt IaC i denne fasen.

## Sikkerhetsstatus

Identity-MVP-en bruker e-postbaserte engangslenker, serverstyrte ugjennomsiktige Cosmos-sesjoner, `HttpOnly`-cookie og CSRF-token. Onboarding bekrefter e-postadressen før betalingsvalg og gårdsopprettelse. `Farm` er tenant-modellen, og en aktiv `FarmUser`-tilknytning er den autoritative kilden til tilgang. `GET /api/me` returnerer bruker, sesjon, CSRF-token, aktive medlemskap og en validert aktiv gård. Rå sesjonstoken og e-postadresser lagres ikke i Identity-oppslagsdokumenter.

`IDENTITY_HMAC_KEY` må settes som en separat Function App-hemmelighet før innlogging kan brukes; Identity-rutene feiler lukket når den mangler. Cosmos-containere opprettes og valideres bare med et eksplisitt, manuelt bootstrap-steg. Farm-, bilags-, dokument-, transaksjons- og rapport-ruter er medlemskaps- og permission-beskyttet. Beskyttede Blob-filer lastes ned via autorisert API-streaming, ikke varige Blob-URL-er. Farm eier ett statisk, versjonert abonnement med effektive entitlements beregnet server-side. Usage og betaling er ikke implementert. Ory/Kratos, Better Auth, SQLAlchemy og PostgreSQL er ikke del av løsningen.

Et eventuelt tidligere Ory-prosjekt må slettes eller deaktiveres manuelt i Ory-konsollen; repositoryet kan ikke gjøre dette.

## Abonnement og tilgang

Hver Farm har ett abonnement i `subscriptions` med partisjonsnøkkel `/farm_id`. Planene `free`, `standard` og `premium` er statiske og versjonerte i backend. Nye Farms får `free` før de aktiveres, og `/api/me` initialiserer bare aktiv eksisterende Farm når abonnement mangler. Frontend får en sikker plan- og entitlement-projeksjon fra `/api/me`, mens API-et kontrollerer den på nytt. Usage og betaling er ikke implementert.

## Lokal utvikling

**Forutsetninger**: Python 3.11+, Node.js 20+, Azure Cosmos DB-emulator eller Azure-tilgang.

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

For Identity må lokal eller driftssatt konfigurasjon også ha en unik `IDENTITY_HMAC_KEY`. Ikke gjenbruk JWT- eller andre integrasjonshemmeligheter.

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

## Cosmos-bootstrap

Kjør manuelt fra repository-roten etter å ha satt lokale backend-miljøvariabler:

```bash
python backend/scripts/bootstrap_cosmos.py --dry-run
```

Skriptet kjører aldri ved Function App-start eller deploy. Se [Cosmos-bootstrap](./docs/COSMOS_BOOTSTRAP.md) for `--validate-only`, database-overstyring og sikkerhetsregler.

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
- [Cosmos-bootstrap](./docs/COSMOS_BOOTSTRAP.md)
- [Identity-MVP](./docs/IDENTITY.md)
- [Farm-medlemskap og tenant-isolasjon](./docs/FARM_MEMBERSHIP.md)
- [Tenant-sikring av regnskap og dokumenter](./docs/TENANT_ACCOUNTING.md)
- [Abonnement og entitlements](./docs/SUBSCRIPTIONS.md)
- [Release gate](./docs/RELEASE_GATE.md)
- [Smoke tests](./docs/SMOKE_TESTS.md)
- [Staging-oppsett](./docs/STAGING_SETUP.md)
- [Produktbacklog](./backlog/epics.md)
- [Statusrapport](./STATUS_REPORT.md)
- [Sjekkliste](./CHECKLIST.md)

## Kontakt

Prosjektet utvikles for norske gårdsbruk og landbruksforetak. Se produktbacklogen for planlagte funksjoner og prioriteringer.

## Neste planlagte fase

`Kontrollert håndtering av legacy-dokumenter med blob_url`.
