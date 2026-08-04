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
- [x] CSRF-beskyttelse og `/api/me` med bruker, sesjon og CSRF-token.
- [x] Autoritativ `FarmUser`-medlemskapsmodell, roller og sentrale permissions for Farm-ruter.
- [x] Tenant-isolerte Farm-ruter og servervalidert aktiv Farm i `/api/me`.
- [x] Abonnement og entitlements per gård.
- [ ] Usage per gård.
- [x] Tenant-sikring av bilag, dokumentmetadata, bokføring, transaksjonslisting, rapporter og Blob-nedlasting.
- [ ] Rate limiting, sikkerhetsgjennomgang og penetrasjonstest.

E-postlenker er Identity-MVP, ikke en abonnementskilde. Ikke legg identitet eller rettigheter i `localStorage`; onboarding lagrer bare en kortvarig UX-kladd lokalt frem til e-postlenken er brukt. `IDENTITY_HMAC_KEY` må være satt før Identity-rutene aktiveres.

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
