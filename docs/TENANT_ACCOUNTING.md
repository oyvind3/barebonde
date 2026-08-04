# Tenant-sikring av regnskap og dokumenter

`Farm` er tenant for økonomi- og dokumentdata. Alle ruter under `/api/farms/{farm_id}` validerer en serverstyrt sesjon, aktivt `FarmUser`-medlemskap og en statisk permission fra `backend/app/core/permissions.py`. Manglende medlemskap og ressurser i en annen Farm returnerer `404`; et aktivt medlem uten tillatelse får `403`.

## Sikrede ruter

- `POST /api/farms/{farm_id}/vouchers`: `voucher.create` og CSRF.
- `GET /api/farms/{farm_id}/vouchers` og `GET /api/farms/{farm_id}/vouchers/{voucher_id}`: `voucher.read`.
- `POST /api/farms/{farm_id}/vouchers/{voucher_id}/book`: `voucher.book` og CSRF.
- `GET /api/farms/{farm_id}/documents` og `GET /api/farms/{farm_id}/documents/{document_id}`: `document.read`.
- `GET /api/farms/{farm_id}/documents/{document_id}/download`: `document.download`.
- `GET /api/farms/{farm_id}/transactions`: `transaction.read`.
- `GET /api/farms/{farm_id}/reports/{monthly|vat|grants|journal}`: `report.basic.read`.
- `GET /api/farms/{farm_id}/reports/liquidity`: `report.advanced.read` og `reports.advanced.enabled`.

`/api/accounting/accounts` er fortsatt et offentlig, statisk oppslagsendepunkt og inneholder ingen tenant-data. De tidligere globale `/api/accounting/vouchers...`- og `/api/accounting/reports...`-rutene er fjernet; frontend bruker bare Farm-scopede paths.

## Permission og entitlement

Likviditetsrapporten `GET /api/farms/{farm_id}/reports/liquidity` er den første avanserte rapporten. Serveren kontrollerer først `report.advanced.read` fra FarmUser-rollen og deretter Farmens Subscription-status og `reports.advanced.enabled`. En `staff`-bruker blir dermed stoppet før Subscription leses, mens owner på `free` får entitlement-avslag. Måneds-, MVA-, tilskudds- og journalrapportene er fortsatt grunnrapporter på `free`.

## Ressurser og Cosmos

Dokumenter og transaksjoner leses med `farm_id` som Cosmos-partisjon. En dokument- eller bilags-ID slås aldri opp globalt når Farm er kjent. Farm-ID fra path er eneste selector; et eventuelt `farm_id` i opplastingsskjema som avviker fra path avvises. Bruker-ID settes alltid fra sesjonsprincipal.

Bokføring oppretter en deterministisk transaksjons-ID per bilag. Gjentatt bokføring returnerer konflikt, og feil mellom opprettelse av transaksjon og oppdatering av bilag forsøker å rydde opp transaksjonen.

## Blob og OCR

MVP-en bruker API-streaming. Etter autorisert dokumentoppslag henter API-et én privat Blob og svarer med `Content-Disposition: attachment` og `X-Content-Type-Options: nosniff`. Liste- og metadataresponser returnerer aldri `blob_url`, SAS eller lagringshemmeligheter. Eldre `blob_url` kan eksistere i lagrede dokumenter, men brukes ikke som fallback for tilgang.

Nye Blob-navn bygges på serveren som `{farm_id}/{document_id}/document.{extension}`. Lagringscontaineren opprettes ikke av runtime. Dersom Cosmos-metadata ikke kan lagres etter en opplasting, forsøker API-et best-effort sletting av Bloben og returnerer ikke suksess.

OCR kjører bare som del av den autoriserte opplastingsflyten og mottar filinnholdet som allerede er bundet til riktig Farm. Det finnes ingen rute som tar vilkårlig Blob-URL fra klienten. Leverandørdetaljer fra OCR-feil sendes ikke til klienten.

## Frontend og avgrensninger

Bilag-, rapport- og dashboard-sider henter aktiv Farm via `/api/me`; `localStorage` kan bare foreslå sist valgte Farm. Felles API-klient sender `credentials: include` og CSRF-token for mutasjoner. Direkte Blob-lenker er erstattet av en autorisert nedlastingsrequest.

Denne fasen legger ikke til Subscription, Entitlements eller Usage. Generiske dokumenter, dokumentoppdatering/-sletting og eksterne transaksjons-CRUD-ruter finnes ikke i dagens produkt og er derfor ikke introdusert her.
