# Abonnement og entitlements

`Farm` eier ett gjeldende Subscription-dokument i Cosmos-containeren `subscriptions`, partisjonert på `/farm_id`. Dokument-ID-en er deterministisk: `subscription:{farm_id}`. Subscription lagrer plan-kode, plan-versjon, status og relevante livssyklusdatoer; entitlements kopieres ikke inn i dokumentet.

## Planer

Planene er statiske og versjonerte i `backend/app/subscriptions/plans.py`. Aktiv versjon er `2026-08` med `free`, `standard` og `premium`. Katalogen inneholder funksjonsflagg, men ikke priser eller usage-kvoter. Ukjent plan eller katalogversjon gir ingen entitlements.

`GET /api/plans` er offentlig og returnerer kun plan-kode, visningsnavn og funksjonsoppsummering.

## Initialisering

Nye Farms følger denne rekkefølgen:

```text
provisioning Farm -> owner FarmUser -> free Subscription -> active Farm
```

Mislykkes opprettelsen av Subscription, forblir Farm `provisioning` og samme autoriserte oppretter kan prøve på nytt. En eksisterende Subscription overskrives aldri. For eldre Farms oppretter `/api/me` bare aktiv Farm sitt manglende `free/active`-abonnement etter medlemskapskontroll.

Det manuelle, idempotente skriptet nedenfor er ikke koblet til Function App-start eller deploy, og oppretter aldri containere:

```bash
python backend/scripts/migrations/004_create_free_subscriptions.py --dry-run
```

## Autorisering

Permission kommer fra aktiv FarmUser-rolle, mens entitlement kommer fra Farmens Subscription og den statiske plankatalogen. Serveren kontrollerer rekkefølgen sesjon, aktiv bruker, aktivt medlemskap, nødvendig permission, Subscription-status og til slutt entitlement. `GET /api/farms/{farm_id}/subscription` krever `subscription.read`; `GET /api/farms/{farm_id}/entitlements` krever aktivt medlemskap. Andre tenants skjules som `404`.

Statuspolicyen er sentral: `active`, `trialing` og `past_due` tillater read/export/mutate; `grace_period`, `canceled` og `expired` tillater read/export; `suspended` og ukjent status gir ingen tilgang.

## Første gate

Likviditetsrapporten `GET /api/farms/{farm_id}/reports/liquidity` krever `report.advanced.read` og `reports.advanced.enabled`. `free` beholder måneds-, MVA-, tilskudds- og journalrapporter, mens `standard` og `premium` kan bruke likviditetsrapporten dersom FarmUser-rollen også tillater det.

`GET /api/me` returnerer bare en sikker Subscription-projeksjon og effektive entitlements for aktiv Farm. Frontend bruker dette som UX-data for plan og låst funksjon; den kan aldri autorisere et API-kall selv.

## Avgrensninger

`billing_method` og `billing_email` er fremtidige betalingspreferanser, ikke Subscription-status. Fasen har ingen betaling, checkout, provider-webhooks, fakturering, usage, kvoter, planendring eller entitlement-overrides.
