# Barebonde – gjeldende sjekkliste

## Bekreftet repository-baseline

- [x] Next.js 14-frontend med statisk eksport til Azure Static Web Apps.
- [x] FastAPI pakket som Azure Functions `AsgiFunctionApp`.
- [x] Cosmos DB-dokumentmodeller og Blob Storage-tjeneste.
- [x] BRREG-, OCR- og Plunk-integrasjoner i backend.
- [x] GitHub Actions for frontend og backend.
- [x] Lokale backend-tester uten krav om Azure-ressurser.

## Ikke produksjonsklart ennå

- [ ] Serverstyrte sesjoner i Cosmos med `HttpOnly`-cookie.
- [ ] CSRF-beskyttelse og `/api/me`.
- [ ] Autoritativ `FarmUser`-medlemskapsmodell og permissions.
- [ ] Abonnement, entitlements og usage per gård.
- [ ] Rate limiting, sikkerhetsgjennomgang og penetrasjonstest.

Google- og e-postflyten er ikke en produksjonsklar identitets- eller abonnementskilde. Ikke legg identitet eller rettigheter i `localStorage`.

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

Azure- og Cloudflare-konfigurasjon håndteres manuelt i MVP-en. Ikke kjør Cosmos-bootstrap eller opprett containere som del av lokal testkjøring.
