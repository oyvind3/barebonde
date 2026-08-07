# Smoke tests – Epic 1

Manuelle smoke tests som skal kjøres i staging før release. Testene dekker
kjernereisen i `docs/RELEASE_GATE.md`. Kjør testene i rekkefølge i en ren
nettleser (gjerne inkognito) med tilgang til staging-miljøet.

## Forberedelser

- Staging-frontend og Function App er deployert med siste versjon.
- Cosmos-containere er bootstrappet (`python backend/scripts/bootstrap_cosmos.py --validate-only`).
- `IDENTITY_HMAC_KEY` er satt i Function App.
- Plunk-nøkler er satt dersom magic link / glemt passord skal testes.

## Test 1: Registrering

1. Åpne frontend og velg registrering.
2. Opprett en ny bruker med en unik e-postadresse og et sterkt passord.
3. **Forventet**: kontoen opprettes, og brukeren havner i onboarding.

## Test 2: Innlogging

1. Logg ut dersom du er innlogget.
2. Logg inn med e-post og passord.
3. **Forventet**: innlogging lykkes, sesjonscookie settes (`HttpOnly`), og
   `/api/me` returnerer bruker og CSRF-token.

## Test 3: Magic link (valgfri hvis Plunk er konfigurert)

1. Velg «Logg inn med lenke» på innloggingssiden.
2. Åpne e-posten og klikk lenken.
3. **Forventet**: brukeren logges inn uten passord.

## Test 4: Farm

1. Gjennomfør onboarding og opprett en ny gård.
2. **Forventet**: Farm opprettes med `free`-abonnement, og `/api/me`
   returnerer Farmen som aktiv.

## Test 5: Bilagsopplasting og OCR

1. Gå til «Nytt bilag».
2. Last opp en PDF eller et bilde av en faktura.
3. **Forventet**:
   - behandlingsstatus vises under opplasting/OCR,
   - dokumentet vises ved siden av skjemaet,
   - OCR-forslag fylles inn i redigerbare felt,
   - usikre eller manglende felt markeres med «Kontroller».

## Test 6: Korrigering og lagring

1. Endre minst ett OCR-forslag (f.eks. totalbeløp eller leverandør).
2. Klikk «Lagre verdier».
3. **Forventet**: verdiene lagres, og en bekreftelse vises.

## Test 7: Bokføring

1. Fyll inn påkrevde felt (totalbeløp > 0, fakturadato, beskrivelse, regnskapskonto).
2. Klikk «Bokfør bilag».
3. **Forventet**:
   - bilaget får status «ført»,
   - en tydelig suksess-state vises,
   - bilaget er synlig i bilagslisten.

## Test 8: Logout og login igjen

1. Logg ut.
2. **Forventet**: sesjonen tilbakekalles, og beskyttede sider krever innlogging.
3. Logg inn igjen med samme bruker.
4. **Forventet**: det bokførte bilaget fra test 7 er fortsatt synlig.

## Test 9: Tenant-isolasjon (valgfri, krever to brukere)

1. Opprett en andre bruker med egen Farm.
2. Forsøk å hente bilag fra den første Farmen med den andre brukerens sesjon.
3. **Forventet**: 404 eller 403 – ingen tilgang på tvers av Farms.

## Resultat

Alle obligatoriske tester må bestå før release-gaten i `docs/RELEASE_GATE.md`
kan godkjennes. Dokumenter eventuelle avvik som saker i backlogen.