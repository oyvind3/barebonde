# Salgsfaktura (Epic 3)

Barebonde har en enkel, farm-scoped salgsfakturaflyt:

```text
Velg/opprett kunde
→ opprett fakturautkast
→ legg til fakturalinjer
→ backend beregner MVA og total
→ forhåndsvis PDF (UTKAST)
→ utsted faktura (fakturanummer + snapshots + permanent PDF)
→ send PDF på e-post (Plunk)
→ se status
→ marker betalt (manuelt)
```

## Datamodell

To nye Cosmos-containere, begge med partition key `/farm_id`:

- `customers` – farm-scoped kunderegister (MVP, ikke CRM)
- `sales_invoices` – salgsfakturaer med status, linjer og snapshots

Begge registreres sentralt i `backend/app/db/cosmos_schema.py` og
opprettes/valideres av `backend/scripts/bootstrap_cosmos.py`. Containere
opprettes aldri fra request handlers.

Fakturanummer-sekvens lagres som et eget dokument
(`sales-invoice-sequence:<farm_id>:<year>`) i `sales_invoices`-containeren,
og oppdateres med optimistic concurrency (ETag) slik at to samtidige
issue-kall aldri får samme nummer. Nummer gjenbrukes aldri.

## Kunde

- `name` er påkrevd; `email` kan være tom inntil faktura skal sendes.
- `org_number` er valgfritt (privat kunde) og normaliseres til 9 siffer.
- BRREG-søk (`search_orgs` / `lookup_org`) brukes som prefill; bruker kan
  korrigere adresse/e-post. E-post må normalt legges inn manuelt.
- Duplikater innen samme farm unngås ved oppslag på org.nr.

## Livssyklus

```text
draft → issued → sent → paid
draft → cancelled
```

| Status    | Betydning |
|-----------|-----------|
| `draft`   | Kan redigeres, forhåndsvises og kanselleres. Har ikke fakturanummer. |
| `issued`  | Permanent fakturanummer, snapshots og PDF. Kan sendes og markeres betalt. |
| `sent`    | Plunk har akseptert utsending. Kan sendes på nytt og markeres betalt. |
| `paid`    | Manuelt markert betalt (`paid_at` satt). |
| `cancelled` | Kun for utkast. Utstedte fakturaer kanselleres ikke (kreditnota kommer senere). |

`issued`, `sent` og `paid` er immutable. PATCH gjelder kun `draft` og gir
409 dersom fakturaen ikke er et utkast.

## Snapshots

Ved utstedelse fryses:

- **Selger**: juridisk navn, org.nr., adresse, postnummer/sted, kontakt,
  MVA-status/-nummer fra farm settings.
- **Betaling**: kontonummer fra valgt/standard bankkonto.
- **Kunde**: navn, org.nr., e-post, adresse, postnummer/sted, land.

Senere endringer i farm settings, kunde eller bankkonto endrer ikke en
utstedt faktura.

## Beregning

- Alle beløp lagres som heltall i øre.
- Antall håndteres som `Decimal`; backend beregner alle summer autoritativt.
- Avrunding: `ROUND_HALF_UP` per linje (net, VAT, total), deretter summering.
- Støttede MVA-satser: 0, 12, 15, 25.
- Valuta: NOK kun.
- Frontend viser kun preview; totalsummer fra frontend stoles aldri på.

## Fakturanummer

- Tildeles først ved issue, format `ÅÅÅÅ-NNNN` (f.eks. `2026-0001`).
- Unikt per farm og år, concurrency-sikkert via ETag-retry på
  sekvensdokumentet.
- Immutable og gjenbrukes aldri.

## PDF

- Genereres på backend med ReportLab (ingen Chromium/systemavhengigheter).
- Utkast merkes tydelig `UTKAST` og lagres ikke permanent.
- Utstedt faktura får permanent PDF som lagres privat i Azure Blob Storage.
- Nedlasting går via autorisert endpoint
  `GET /api/farms/{farm_id}/sales-invoices/{invoice_id}/pdf` som streamer
  `application/pdf`. Ingen permanent offentlig Blob URL.

## E-post (Plunk)

- Felles Plunk-helper er flyttet til `backend/app/services/email_service.py`
  (`send_transactional_email`); auth bruker samme service.
- Faktura sendes med PDF-vedlegg, kort norsk tekst (fakturanummer, selger,
  beløp, forfall). Ingen Barebonde-markedsføring.
- Idempotency-Key: `sales-invoice:<invoice_id>:send:<attempt>` hindrer
  dobbeltsending. `send_count` styres server-side.
- Ved provider-feil forblir status `issued`, `sent_at` settes ikke, og kun
  sanitert feil lagres i `delivery.last_error`.

## Permissions

Utvidet `Permission`-enum:

```text
customer.read / customer.create / customer.update
sales_invoice.read / sales_invoice.create / sales_invoice.update
sales_invoice.issue / sales_invoice.send / sales_invoice.mark_paid
```

- **owner**: alle permissions.
- **manager**: hele fakturaflyten (lese, opprette, redigere, utstede, sende,
  markere betalt).
- **staff**: kun lese kunder og salgsfakturaer.

Alle muterende ruter bruker `require_farm_permission(...)` og eksisterende
CSRF-beskyttelse. Issue/send/resend er klassifisert konservative i
rate limiter.

## Regnskapsgrense

- `paid` er en manuell betalingsstatus. Det opprettes ingen banktransaksjon,
  journal entry eller bokføring.
- Salgsfaktura er et eget domeneobjekt og er ikke koblet til dagens enkle
  `transactions`-modell.
- Automatisk bokføring av salgsfaktura kommer i Epic 4 sammen med en
  ordentlig journal/debet-kredit-modell.
- EHF/Peppol/ELMA/Altinn er ikke implementert og kommer senere.

## Frontend

- `/faktura` – fakturaliste med status, Forfalt-indikator og CTA.
- `/faktura/ny` – kunde (eksisterende/ny/BRREG), detaljer, linjer, summer,
  lagre utkast, forhåndsvis, utsted.
- `/faktura/detalj?id=...` – statusbaserte handlinger (send, send på nytt,
  marker betalt, last ned PDF, kanseller utkast).
- `/kunder` – søk, liste, ny kunde med BRREG-prefill, redigering.
- `Faktura` og `Kunder` er lagt inn i navigasjonen; dashboard har CTA og
  teller for ubetalte fakturaer.