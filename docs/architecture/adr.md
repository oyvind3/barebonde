# Barebonde – arkitekturbeslutninger

## ADL-001: Plattform og deploymodell

**Status:** Besluttet

Barebonde bruker Next.js 14 med statisk eksport på Azure Static Web Apps og FastAPI i én Python Azure Functions v4 `AsgiFunctionApp`. Eksisterende GitHub Actions beholdes. Azure- og Cloudflare-konfigurasjon håndteres manuelt i MVP-en; det er ikke planlagt IaC nå.

## ADL-002: Datamodell og tenancy

**Status:** Delvis implementert

Azure Cosmos DB er dokumentdatabasen. Gårdsobjekter, brukerprofiler og gårdstilknytninger lagres som dokumenter, og Azure Blob Storage lagrer dokumentfiler. `Farm` er tenanten. `FarmUser` er autoritativ medlemskaps- og autoriseringskontroll for Farm-rutene. Regnskaps- og Blob-ruter sikres videre i neste fase.

## ADL-003: Identity og autorisering

**Status:** Delvis implementert

Identity bruker e-postbasert engangsinnlogging. Sesjoner er ugjennomsiktige, serverstyrte Cosmos-dokumenter; bare et tilfeldig token ligger i en `HttpOnly`-cookie. `identity_lookups` bruker HMAC-baserte, formålsbundne ID-er for e-post. `/api/me` eksponerer bruker, sesjon, aktive medlemskap og aktiv Farm, og CSRF-token kreves for muterende ruter.

`users` beholder den eksisterende `/better_auth_id`-partisjonsnøkkelen. FarmUser brukes som autoritativ tenant- og rollekontroll for Farm-ruter. Abonnement og entitlements er fortsatt ikke implementert.

Ory/Kratos, Better Auth, SQLAlchemy, PostgreSQL og ID-porten er ikke del av målarkitekturen.

## ADL-004: Regnskap og dokumenter

**Status:** Delvis implementert

Regnskap og bilag er én modul, ikke hele produktet. Bilagsmetadata lagres i Cosmos, mens dokumentinnhold lagres i Azure Blob Storage. OCR og BRREG holdes som integrasjoner i samme Function App.

## ADL-005: Videre modularisering

**Status:** Planlagt

Identity, organisasjoner, abonnement, entitlements og autorisering skal organiseres som moduler i den eksisterende Function App. De er ikke egne mikroservicer i MVP-en, men skal kunne skilles ut dersom drift eller skala senere krever det.

## ADL-006: Eksplisitt Cosmos-bootstrap

**Status:** Implementert

Database- og containeropprettelse, samt partisjonsnøkkelvalidering, er flyttet ut av Function App-livssyklusen til `backend/scripts/bootstrap_cosmos.py`. Den sentrale definisjonen i `backend/app/db/cosmos_schema.py` brukes av både runtime og skriptet. Bootstrap er manuelt, idempotent og ikke-destruktivt: det oppretter bare manglende ressurser og feiler ved en eksisterende partisjonsnøkkelkonflikt.

## Neste arkitekturarbeid

`Tenant-sikring av bilag, dokumenter, bokføring, rapporter og Blob-tilgang`.
