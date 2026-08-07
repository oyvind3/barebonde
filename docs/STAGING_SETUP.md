# Staging-oppsett – Barebonde

Denne filen beskriver faktisk konfigurasjon for staging-miljøet, basert på koden.
Ingen ekte secrets er inkludert – alle hemmeligheter settes som miljøvariabler i
Azure Function App.

## Arkitektur

- **Backend**: FastAPI-app deployert som Azure Function App (HTTP-trigger).
- **Frontend**: Next.js-app deployert som Azure Static Web App.
- **Database**: Azure Cosmos DB (NoSQL).
- **Fillagring**: Azure Blob Storage for bilagsfiler.
- **OCR**: Azure AI Document Intelligence.
- **E-post**: Plunk (valgfritt).

## Miljøvariabler – Function App

### Cosmos DB

| Variabel | Beskrivelse | Standardverdi |
|---|---|---|
| `COSMOS_DB_CONNECTION_STRING` | Tilkoblingsstreng til Cosmos DB | (påkrevd) |
| `COSMOS_DB_DATABASE_ID` | Databasenavn | `barebonde` |

Containerne bootstrappes med `python backend/scripts/bootstrap_cosmos.py`.

### Blob Storage

| Variabel | Beskrivelse | Standardverdi |
|---|---|---|
| `AZURE_STORAGE_CONNECTION_STRING` | Tilkoblingsstreng til Blob Storage | `""` |
| `AZURE_STORAGE_CONTAINER_NAME` | Container for bilagsfiler | `bilag` |

### Identity / session

| Variabel | Beskrivelse | Standardverdi |
|---|---|---|
| `IDENTITY_HMAC_KEY` | HMAC-nøkkel for signering av sesjonstokens | `""` (påkrevd i prod) |
| `IDENTITY_SESSION_TTL_SECONDS` | Sesjonslevetid | `604800` (7 dager) |
| `IDENTITY_MAGIC_LINK_TTL_SECONDS` | Levetid for magic link | `900` (15 min) |
| `IDENTITY_COOKIE_NAME` | Navn på sesjonscookie | `barebonde_session` |
| `IDENTITY_COOKIE_SECURE` | Tving `Secure`-flagg på cookie | `None` (auto) |
| `INVITATION_TTL_SECONDS` | Levetid for invitasjoner | `604800` (7 dager) |
| `INVITATION_RESEND_COOLDOWN_SECONDS` | Nedkjøling før ny invitasjon kan sendes | `60` |

Sesjoner lagres i Cosmos DB og tilbakekalles server-side ved logout.

### Cookies og CSRF

- Sesjonscooki er `HttpOnly`, `SameSite=Lax`, og `Secure` i produksjon.
- CSRF-token utstedes via `/api/me` og må sendes som `X-CSRF-Token`-header
  på alle muterende forespørsler.
- Ingen rå tokens lagres i `localStorage`.

### CORS

| Variabel | Beskrivelse |
|---|---|
| `CORS_ORIGINS` | Kommaseparert liste over tillatte origins |

Standardverdier i koden:

```
http://localhost:3000
http://localhost:3001
https://barebonde.no
https://www.barebonde.no
https://salmon-ocean-076260203.7.azurestaticapps.net
```

I staging må `CORS_ORIGINS` inkludere Static Web App-URL-en.

### Frontend URL

| Variabel | Beskrivelse | Standardverdi |
|---|---|---|
| `FRONTEND_URL` | Base-URL for frontend (brukes til redirects) | `http://localhost:3000` |

I staging settes denne til Static Web App-URL-en.

### API URL

Frontend kaller Function App direkte. URL-en konfigureres i frontend via
`NEXT_PUBLIC_API_URL` (se `frontend/.env.example`).

### Plunk (e-post)

| Variabel | Beskrivelse | Standardverdi |
|---|---|---|
| `PLUNK_SECRET_API_KEY` | Hemmelig API-nøkkel for Plunk | `""` |
| `PLUNK_PUBLIC_API_KEY` | Offentlig API-nøkkel for Plunk | `""` |

Magic link og glemt passord krever at Plunk-nøklene er satt.

### BRREG

Brreg-tjenesten brukes for virksomhetsoppslag under onboarding. Ingen nøkler
kreves – tjenesten kaller Brreggs åpne API.

### OCR

| Variabel | Beskrivelse | Standardverdi |
|---|---|---|
| `AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT` | Endpoint for Document Intelligence | `""` |
| `AZURE_DOCUMENT_INTELLIGENCE_KEY` | API-nøkkel for Document Intelligence | `""` |
| `OCR_DEFAULT_LANGUAGE` | Standardspråk for OCR | `nb` |

### Rate limiting

Rate limiting er implementert som in-memory middleware i FastAPI.

| Endepunkttype | Grense |
|---|---|
| Registrering | 5 forespørsler / minutt |
| Innlogging / magic link | 10 forespørsler / minutt |
| E-post | 3 forespørsler / minutt |
| Onboarding | 30 forespørsler / minutt |
| Øvrige | 100 forespørsler / minutt |

**Kjent begrensning**: Rate limiting er in-memory per instans. Ved skalering
til flere instanser eller restart tilbakestilles tellerne. For produksjon med
flere instanser bør Redis-basert rate limiting vurderes.

### Trusted proxies

Rate limiteren stoler på `X-Forwarded-For` og `X-Real-IP` fra følgende nettverk:

```
10.0.0.0/8
172.16.0.0/12
192.168.0.0/16
127.0.0.1
```

Dette dekker Azure-infrastruktur. Direkte tilkoblinger fra ikke-klarerte IP-er
brukes som klient-IP uten å stole på headers.

## Azure Functions

- Backend kjører som en Azure Function App med HTTP-trigger.
- `function_app.py` er inngangspunktet.
- `host.json` konfigurerer Function App-oppførsel.
- Deploy via GitHub Actions: `.github/workflows/main_barebonde.yml`.

## Azure Static Web Apps

- Frontend deployes som Azure Static Web App.
- Deploy via GitHub Actions: `.github/workflows/azure-static-web-apps-salmon-ocean-076260203.yml`.
- `NEXT_PUBLIC_API_URL` må peke på Function App-URL-en i staging.

## Kjente begrensninger

- **Rate limiting**: in-memory per instans – tilbakestilles ved restart/skalering.
- **OCR**: Azure Document Intelligence har begrensninger i nøyaktighet, særlig
  for håndskrift, lav oppløsning og uvanlige fakturaformater. OCR-forslag skal
  alltid kontrolleres av brukeren.
- **Regnskapssystem**: Barebonde er foreløpig ikke et komplett regnskapssystem.
  EHF, Peppol, Altinn, MVA-innsending, betaling, bankintegrasjon og komplett
  hovedbok er ikke implementert.