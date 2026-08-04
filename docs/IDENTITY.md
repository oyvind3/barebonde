# Identity-MVP

Barebonde bruker fortsatt én FastAPI-basert Azure Function App. Identity er en modul i samme deploybare enhet, ikke en ny tjeneste.

## Flyter

- `POST /api/auth/google` validerer Google ID-token på serveren, løser Google-subjekt/e-post til en intern `user_id`, oppretter en Cosmos-sesjon og setter en `HttpOnly`-cookie.
- `POST /api/auth/magic-link` oppretter en e-postbasert utfordring som kan brukes én gang. Plunk leverer lenken.
- `POST /api/auth/magic-link/verify` bruker utfordringen én gang og oppretter sesjonen.
- `GET /api/me` returnerer bare bruker, gjeldende sesjon og CSRF-token.
- `POST /api/auth/logout`, `GET /api/auth/sessions` og `DELETE /api/auth/sessions/{session_id}` gir avslutning og egen sesjonsoversikt. Muterende sesjonsruter krever `X-CSRF-Token`.

## Cosmos-data

- `users` beholder `/better_auth_id` som partisjonsnøkkel. Nye dokumenter får additive felter som `user_id`, `status`, `email_normalized`, `identity_version` og tidsstempler.
- `identity_lookups` er partisjonert på `/lookup_partition_id`. ID-en er en HMAC med `IDENTITY_HMAC_KEY`; dokumentet lagrer ikke rå e-post eller rå Google-subjekt.
- `auth_challenges` har én e-postutfordring per dokument og lagrer bare intern brukerreferanse, utløp og forbrukstid.
- `auth_sessions` har bare en HMAC-basert sesjons-ID, intern brukerreferanse, utløp og tilbakekalling. Det tilfeldige cookie-tokenet lagres aldri i Cosmos.

Kjør det manuelle [Cosmos-bootstrap-skriptet](./COSMOS_BOOTSTRAP.md) mot et valgt miljø før disse containerne forventes å finnes. Skriptet er ikke kjørt som del av denne implementasjonen.

## Drift og grenser

Sett en separat, tilfeldig `IDENTITY_HMAC_KEY` i Function App-konfigurasjonen. Ikke gjenbruk en tidligere JWT-, Google- eller Plunk-hemmelighet. Uten nøkkelen feiler Identity-rutene lukket, mens health-endepunktet fortsatt fungerer.

Produksjonsfrontend og API ligger på forskjellige origins i dagens oppsett. CORS tillater `barebonde.no`, og produksjonscookie bruker `SameSite=None; Secure`. Cloudflare/API-domeneoppsett må verifiseres i en ekte nettleser, siden strenge tredjeparts-cookie-regler kan kreve en same-site API-domenevariant. Dette dokumentet endrer ikke Cloudflare eller Azure.

Denne fasen innfører ikke FarmUser-roller, tenant-autorisering, abonnement, entitlements, invites eller betalingsintegrasjon. De eksisterende gårds- og regnskapsrutene blir derfor ikke påstått å være autorisert av Identity ennå.
