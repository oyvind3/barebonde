# Barebonde – statusrapport

**Oppdatert:** 4. august 2026
**Status:** Eksisterende løsning er i aktiv utvikling; dette dokumentet beskriver verifiserbar repository-status, ikke en produksjonsgodkjenning.

## Aktiv arkitektur

- Frontend: Next.js 14 med statisk eksport til Azure Static Web Apps.
- Backend: FastAPI i én Python Azure Functions v4 `AsgiFunctionApp`.
- Data: Azure Cosmos DB (NoSQL) og Azure Blob Storage for dokumenter.
- Leveranse: GitHub Actions-workflows i `.github/workflows/`.
- Drift: Azure og Cloudflare håndteres manuelt. MVP-en har ingen IaC-plan.

## Produktstatus

BRREG-oppslag, gårdsoppsett, bilag/OCR og Plunk-integrasjon finnes i repositoryet. Google Identity Services og den nåværende e-postflyten brukes i onboarding, men er ikke en produksjonsklar identitets- eller autoriseringsløsning. Det finnes ennå ikke serverstyrte sesjoner, CSRF-beskyttelse, autoritativt medlemskap eller sentral permission-kontroll.

Cosmos DB er den faktiske datalagringen. SQLAlchemy, PostgreSQL, Better Auth, ID-porten og Ory/Kratos er ikke aktive deler av dagens arkitektur.

## Neste arbeid

1. Eksplisitt Cosmos bootstrap og validering av eksisterende containere.
2. Serverstyrt Identity med sesjoner og `HttpOnly`-cookies.
3. FarmUser-medlemskap og sentral autorisering.

Ingen av disse stegene er gjennomført av denne statusrapporten.
