# Identity-MVP

Barebonde bruker fortsatt én FastAPI-basert Azure Function App. Identity er en modul i samme deploybare enhet, ikke en ny tjeneste.

## Flyter

- `POST /api/auth/email/request` sender bare innloggingslenke til en eksisterende konto. En ukjent e-postadresse oppretter verken bruker, oppslag eller utfordring.
- `POST /api/auth/register/email/request` oppretter en `email_registration`-utfordring for en ny e-postadresse. `User` opprettes først når lenken verifiseres.
- `POST /api/auth/register` er beholdt for eldre gårdsoppsett, men starter nå bare samme e-postverifisering og oppretter ikke brukerprofil på forhånd.
- `POST /api/auth/magic-link/verify` bruker en `email_login`- eller `email_registration`-utfordring én gang, markerer e-posten som verifisert og oppretter sesjonen.
- `GET /api/me` returnerer bruker, gjeldende sesjon, CSRF-token og aktive Farm-medlemskap. Den aktive gården er alltid validert mot de aktive medlemskapene.
- `POST /api/auth/logout`, `GET /api/auth/sessions` og `DELETE /api/auth/sessions/{session_id}` gir avslutning og egen sesjonsoversikt. Muterende sesjonsruter krever `X-CSRF-Token`.

## Cosmos-data

- `users` beholder `/better_auth_id` som partisjonsnøkkel. Nye dokumenter får additive felter som `user_id`, `status`, `email_normalized`, `identity_version` og tidsstempler.
- `identity_lookups` er partisjonert på `/lookup_partition_id`. ID-en er en HMAC med `IDENTITY_HMAC_KEY`; dokumentet lagrer ikke rå e-post.
- `auth_challenges` har én e-postutfordring per dokument. Innloggingsutfordringer lagrer bare intern brukerreferanse; registreringsutfordringer lagrer den normaliserte e-postadressen til den er verifisert. Begge har utløp og forbrukstid.
- `auth_sessions` har bare en HMAC-basert sesjons-ID, intern brukerreferanse, utløp og tilbakekalling. Det tilfeldige cookie-tokenet lagres aldri i Cosmos.

Kjør det manuelle [Cosmos-bootstrap-skriptet](./COSMOS_BOOTSTRAP.md) mot et valgt miljø før disse containerne forventes å finnes. Skriptet er ikke kjørt som del av denne implementasjonen.

## Drift og grenser

Sett en separat, tilfeldig `IDENTITY_HMAC_KEY` i Function App-konfigurasjonen. Ikke gjenbruk en tidligere JWT- eller Plunk-hemmelighet. Uten nøkkelen feiler Identity-rutene lukket, mens health-endepunktet fortsatt fungerer.

Produksjonsfrontend og API ligger på forskjellige origins i dagens oppsett. FastAPI tillater `https://barebonde.no` med credentials, og produksjonscookie bruker `SameSite=None; Secure`. Function App-ens plattform-CORS må ha samme origin og credentials aktivert; plattformen kan ellers stanse preflight før FastAPI mottar requesten. Cloudflare/API-domeneoppsett må verifiseres i en ekte nettleser, siden strenge tredjeparts-cookie-regler kan kreve en same-site API-domenevariant. Dette dokumentet endrer ikke Cloudflare eller Azure.

Identity bestemmer bare hvem brukeren er. `FarmUser` bestemmer hvilken Farm brukeren har tilgang til og hvilke Farm-handlinger rollen tillater; se [Farm-medlemskap](./FARM_MEMBERSHIP.md) og [Tenant-sikring av regnskap og dokumenter](./TENANT_ACCOUNTING.md). Denne fasen innfører ikke abonnement, entitlements, invites eller betalingsintegrasjon.
