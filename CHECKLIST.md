# Barebonde – gjeldende sjekkliste

## Bekreftet repository-baseline

- [x] Next.js 14-frontend med statisk eksport til Azure Static Web Apps.
- [x] FastAPI pakket som Azure Functions `AsgiFunctionApp`.
- [x] Cosmos DB-dokumentmodeller og Blob Storage-tjeneste.
- [x] Manuelt, idempotent Cosmos-bootstrap med partisjonsnøkkelvalidering.
- [x] BRREG-, OCR- og Plunk-integrasjoner i backend.
- [x] GitHub Actions for frontend og backend.
- [x] Lokale backend-tester uten krav om Azure-ressurser.

## Ikke produksjonsklart ennå

- [x] Serverstyrte Cosmos-sesjoner med `HttpOnly`-cookie, logout og tilbakekalling.
- [x] CSRF-beskyttelse og `/api/me` med avgrenset bruker-/sesjonsrespons.
- [ ] Autoritativ `FarmUser`-medlemskapsmodell og permissions.
- [ ] Abonnement, entitlements og usage per gård.
- [ ] Rate limiting, sikkerhetsgjennomgang og penetrasjonstest.

Google- og e-postflyten er Identity-MVP, ikke en abonnementskilde. Ikke legg identitet eller rettigheter i `localStorage`; `IDENTITY_HMAC_KEY` må være satt før Identity-rutene aktiveres.

## Lokal kvalitetssjekk

```bash
cd backend
python -m pytest

cd ../frontend
npm ci
npm run lint
npx tsc --noEmit
npm run build
```

Azure- og Cloudflare-konfigurasjon håndteres manuelt i MVP-en. Ikke kjør Cosmos-bootstrap mot et reelt miljø som del av vanlig lokal testkjøring eller deploy.
