# Barebonde – statusrapport

**Oppdatert:** 8. juli 2026 (Epic 2 – fortsettelse fullført)
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

Rollene `owner`, `manager` og `staff` bruker en sentral, statisk permission-katalog. Opprettelse, lesing, endring og medlemsliste for Farm er tenant-isolert. Bilag, dokumentmetadata, dokumentnedlasting, bokføring, transaksjonslisting og rapporter bruker nå Farm-scope i URL, aktivt medlemskap og permission. Muterende bilagsruter krever CSRF. Nye Blob-navn er bundet til Farm og servergenerert dokument-ID; API-et streamer autoriserte nedlastinger og returnerer ikke varige Blob-URL-er. Hver Farm har ett statisk, versjonert abonnement med serverberegnede entitlements. Usage er fortsatt ikke implementert.

Bilagskontroll-flyten er implementert i `frontend/app/bilag/new/page.tsx`: brukeren laster opp PDF eller bilde, ser behandlingsstatus og dokumentet side ved side med redigerbare OCR-forslag, markerer usikre/manglende felt med «Kontroller», korrigerer verdier, lagrer brukerbekreftede verdier og bokfører bilaget med tydelig success-state. OCR-forslag er forslag; brukerbekreftede verdier er autoritative. Rate limiting er in-memory per instans.

Bilagsdetaljside (`/bilag/[voucherId]`) er implementert via `frontend/app/bilag/detalj/page.tsx` og `frontend/components/bilag/VoucherDetailClient.tsx`. Siden viser dokumentpreview, status, alle OCR-felt og OCR-kontrollstatus. Ikke-bokførte bilag kan redigeres via eksisterende PATCH-endepunkt med delt feltskjema (`frontend/components/bilag/VoucherFields.tsx`). Bokførte bilag låser regnskapskritiske felt (beløp, dato, konto, MVA-kode, transaksjonstype) og tillater kun metadataendring, med forklaring om at korreksjonsflyt kreves.

OCR-feltutvinning (`backend/app/services/invoice_field_parser.py` og `ocr_service.py`) bruker label-basert kandidat-scoring med støtte for norske etiketter (Org.nr, Fakturanr, Fakturadato, Forfallsdato, Å betale, Eks. MVA, MVA, KID), formatvalidering, checksum (KID/modulus), matematisk konsistens (eks. MVA + MVA ≈ total) og datorekkefølge. Konflikter reduserer confidence og legger til warnings som vises som «Kontroller» i frontend.

Cosmos DB er den faktiske datalagringen. SQLAlchemy, PostgreSQL, Better Auth, ID-porten og Ory/Kratos er ikke aktive deler av dagens arkitektur.

## Subscription og entitlements

Hver Farm har ett idempotent `subscriptions`-dokument med en statisk, versjonert plan: `free`, `standard` eller `premium`. Nye Farms får `free` før de aktiveres, og `/api/me` initialiserer bare aktiv eksisterende Farm lazily. `report_liquidity` er første avanserte rapport og krever både rollepermission og `reports.advanced.enabled`; måneds-, MVA-, tilskudds- og journalrapportene forblir grunnrapporter på `free`. Usage og betaling er ikke implementert.

## Neste arbeid

1. Kontrollert håndtering av legacy-dokumenter med `blob_url`.
2. Rate limiting og sikkerhetsgjennomgang av Identity før bred produksjonsbruk.

Se [Release gate](./docs/RELEASE_GATE.md), [Smoke tests](./docs/SMOKE_TESTS.md) og [Staging-oppsett](./docs/STAGING_SETUP.md) for pilotgrunnlag.

Bootstrap-skriptet finnes, men er ikke kjørt mot et reelt Cosmos-miljø som del av repository-arbeidet.
