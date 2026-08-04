# Farm-medlemskap og tenant-isolasjon

`Farm` er Barebonde sin tenant. `FarmUser` i den eksisterende `farm_users`-containeren (`/farm_id`) er den autoritative koblingen mellom en intern bruker og en Farm.

## Medlemskap og roller

Nye medlemskap har en deterministisk ID: `membership:{farm_id}:{user_id}`. De bruker `farm_role` og `membership_status`; eldre dokumenter med bare `role` leses fortsatt bakoverkompatibelt. Bare status `active` gir tilgang.

Rollene er statiske i MVP-en:

- `owner`: alle Farm- og abonnementstillatelser i katalogen.
- `manager`: kan lese og oppdatere Farm, liste medlemmer og lese abonnement.
- `staff`: kan lese Farm.

Permission-katalogen ligger i `backend/app/core/permissions.py`. Rutehåndterere avgjør ikke roller selv.

## Tilgangsmodell

Farm-avgrensede ruter bruker den serverstyrte sesjonen til å hente brukeren og leser medlemskapet på nytt for hver request. Manglende sesjon gir `401`; en Farm uten aktivt medlemskap fremstår som `404`; et aktivt medlem uten riktig permission får `403`.

`POST /api/farms` krever sesjon og CSRF. Den oppretter først Farm med status `provisioning`, oppretter deretter owner-medlemskapet og aktiverer Farm. En retry fra samme oppretter kan fullføre en avbrutt provisioning, men kjennskap til et organisasjonsnummer gir aldri owner-tilgang til en eksisterende Farm.

`GET /api/me` inneholder aktive medlemskap og en validert `active_farm`. Frontend kan lagre sist valgte Farm lokalt bare som en UX-preferanse; den bestemmer aldri tilgang, rolle eller identitet.

## Avgrensninger

Farm-opprettelse, Farm-lesing/-endring og medlemsliste er tenant-sikret i denne fasen. Regnskap, bilag, dokumenter, rapporter og Blob-nedlasting skal få tilsvarende Farm-autorisasjon i neste fase. Subscription, entitlements, usage, invitasjoner, rolleendring og eierskapsoverføring er ikke implementert.

Medlemskap hentes med en begrenset cross-partition-spørring for `/api/me`. Dette er bevisst enkelt i MVP-en og må RU-måles før det optimaliseres med en ny projeksjon.
