# Barebonde – arkitekturbeslutninger

## ADL-001: Plattform og deploymodell

**Status:** Besluttet

Barebonde bruker Next.js 14 med statisk eksport på Azure Static Web Apps og FastAPI i én Python Azure Functions v4 `AsgiFunctionApp`. Eksisterende GitHub Actions beholdes. Azure- og Cloudflare-konfigurasjon håndteres manuelt i MVP-en; det er ikke planlagt IaC nå.

## ADL-002: Datamodell og tenancy

**Status:** Delvis implementert

Azure Cosmos DB er dokumentdatabasen. Gårdsobjekter, brukerprofiler og gårdstilknytninger lagres som dokumenter, og Azure Blob Storage lagrer dokumentfiler. `Farm` er den framtidige tenanten. `FarmUser` finnes som dokumentmodell, men er ennå ikke autoritativ medlemskaps- eller autoriseringskontroll.

## ADL-003: Identity og autorisering

**Status:** Planlagt, ikke implementert

Den nåværende Google- og e-postflyten er overgangsfunksjonalitet og ikke produksjonsklar autentisering. Neste sikkerhetsfase skal etablere serverstyrte sesjoner i Cosmos, `HttpOnly`-cookies, CSRF-beskyttelse og sentrale autoriseringsbeslutninger basert på `FarmUser`.

Ory/Kratos, Better Auth, SQLAlchemy, PostgreSQL og ID-porten er ikke del av målarkitekturen.

## ADL-004: Regnskap og dokumenter

**Status:** Delvis implementert

Regnskap og bilag er én modul, ikke hele produktet. Bilagsmetadata lagres i Cosmos, mens dokumentinnhold lagres i Azure Blob Storage. OCR og BRREG holdes som integrasjoner i samme Function App.

## ADL-005: Videre modularisering

**Status:** Planlagt

Identity, organisasjoner, abonnement, entitlements og autorisering skal organiseres som moduler i den eksisterende Function App. De er ikke egne mikroservicer i MVP-en, men skal kunne skilles ut dersom drift eller skala senere krever det.

## Neste arkitekturarbeid

Før Identity implementeres: `Eksplisitt Cosmos bootstrap og validering av eksisterende containere`.
