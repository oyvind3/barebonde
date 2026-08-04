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

BRREG-oppslag, gårdsoppsett, bilag/OCR og Plunk-integrasjon finnes i repositoryet. Identity-MVP-en bruker e-postbasert engangsinnlogging, Cosmos-baserte ugjennomsiktige sesjoner, `HttpOnly`-cookie, CSRF, logout og sesjonsoversikt. Onboarding lagrer profilopplysninger, sender en e-postbekreftelse og lar brukeren først velge betaling etter at lenken har opprettet en sesjon. BRREG-adresse med postnummer og poststed fylles inn på gårdsprofilen. `FarmUser` er nå den autoritative medlemskapsmodellen: `GET /api/me` returnerer aktive medlemskap og en validert aktiv Farm, og Farm-rutene kontrollerer medlemskap og rolle server-side. `IDENTITY_HMAC_KEY` må konfigureres separat før rutene kan brukes i et miljø.

Rollene `owner`, `manager` og `staff` bruker en sentral, statisk permission-katalog. Opprettelse, lesing, endring og medlemsliste for Farm er tenant-isolert. Bilag, dokumentmetadata, dokumentnedlasting, bokføring, transaksjonslisting og rapporter bruker nå Farm-scope i URL, aktivt medlemskap og permission. Muterende bilagsruter krever CSRF. Nye Blob-navn er bundet til Farm og servergenerert dokument-ID; API-et streamer autoriserte nedlastinger og returnerer ikke varige Blob-URL-er. Abonnement, entitlements og usage er fortsatt ikke implementert.

Cosmos DB er den faktiske datalagringen. SQLAlchemy, PostgreSQL, Better Auth, ID-porten og Ory/Kratos er ikke aktive deler av dagens arkitektur.

## Neste arbeid

1. Free Subscription, statiske plan-definisjoner og Entitlement-gating på én faktisk funksjon.
2. Rate limiting og sikkerhetsgjennomgang av Identity før bred produksjonsbruk.

Bootstrap-skriptet finnes, men er ikke kjørt mot et reelt Cosmos-miljø som del av repository-arbeidet.
