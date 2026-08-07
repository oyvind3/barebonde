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
- [x] Global rate limiting (in-memory per instans) og trusted proxy-håndtering.
- [x] Bilagskontroll-flyt: opplasting, OCR-forslag, korrigering, lagring og bokføring.
- [x] Bilagsdetaljside med dokumentpreview, redigering av ikke-bokførte bilag og låsing av regnskapskritiske felt på bokførte bilag.
- [x] OCR label-scoring med norske etiketter, formatvalidering, checksum og matematisk konsistens.
- [x] Onboarding: 4 steg (bedrift, produksjon, kontakt, e-postbekreftelse) – fjernet betalingsvalg og interesser.
- [x] Pilotdokumentasjon: RELEASE_GATE.md, SMOKE_TESTS.md og STAGING_SETUP.md.
- [x] Salgsfaktura (Epic 3): farm-scoped kunder og fakturaer, BRREG-prefill, utkast med linjer, backend-autoritativ beregning, concurrency-sikkert fakturanummer, immutable snapshots, ReportLab-PDF i privat Blob, Plunk-utsending med idempotency og manuell «marker betalt».
- [ ] Automatisk bokføring av salgsfaktura (Epic 4).
- [ ] EHF/Peppol for salgsfaktura.
- [ ] Sikkerhetsgjennomgang og penetrasjonstest.
- [ ] Korrigeringsflyt for bokførte bilag (reversering/kreditnota).

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
