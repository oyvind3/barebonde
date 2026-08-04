# Barebonde – statusrapport

**Oppdatert:** 4. august 2026
**Status:** Eksisterende løsning er i aktiv utvikling; dette dokumentet beskriver verifiserbar repository-status, ikke en produksjonsgodkjenning.

## Aktiv arkitektur

- Frontend: Next.js 14 med statisk eksport til Azure Static Web Apps.
- Backend: FastAPI i én Python Azure Functions v4 `AsgiFunctionApp`.
- Data: Azure Cosmos DB (NoSQL) og Azure Blob Storage for dokumenter.
- Cosmos-bootstrap: manuelt `backend/scripts/bootstrap_cosmos.py`; Function App-start og deploy validerer eller oppretter ikke Cosmos-ressurser.
- Leveranse: GitHub Actions-workflows i `.github/workflows/`.
- Drift: Azure og Cloudflare håndteres manuelt. MVP-en har ingen IaC-plan.

## Produktstatus

BRREG-oppslag, gårdsoppsett, bilag/OCR og Plunk-integrasjon finnes i repositoryet. Identity-MVP-en har Google Identity Services, e-postbasert engangsinnlogging, Cosmos-baserte ugjennomsiktige sesjoner, `HttpOnly`-cookie, CSRF, logout, sesjonsoversikt og `/api/me` med bare bruker og sesjon. `IDENTITY_HMAC_KEY` må konfigureres separat før rutene kan brukes i et miljø.

Det finnes fortsatt ikke autoritativt medlemskap, tenant-kontroll eller sentral permission-kontroll. Farm- og abonnementsdata er derfor bevisst utelatt fra `/api/me`.

Cosmos DB er den faktiske datalagringen. SQLAlchemy, PostgreSQL, Better Auth, ID-porten og Ory/Kratos er ikke aktive deler av dagens arkitektur.

## Neste arbeid

1. FarmUser-medlemskap og sentral tenant-autorisering.
2. Abonnement og statiske entitlements per gård.
3. Rate limiting og sikkerhetsgjennomgang av Identity før bred produksjonsbruk.

Bootstrap-skriptet finnes, men er ikke kjørt mot et reelt Cosmos-miljø som del av repository-arbeidet.
