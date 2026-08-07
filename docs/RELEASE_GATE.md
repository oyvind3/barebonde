# Release gate – Epic 1: Pilotbaseline

Denne filen definerer kriteriene for å frigjøre Epic 1 til pilotbrukere. En release
er klar når kjernereisen under kan gjennomføres i staging-miljøet uten manuell
database- eller utviklerinngripen.

## Kjernereise

Reisen som må fungere ende-til-ende:

1. **Registrering** – ny bruker oppretter konto med e-post og passord.
2. **Innlogging** – brukeren logger inn med passord eller magic link.
3. **Farm** – brukeren oppretter eller velger en aktiv gård (tenant).
4. **Bilagsopplasting** – brukeren laster opp en PDF eller et bilde av en faktura.
5. **OCR-kontroll** – systemet viser OCR-forslag i redigerbare felt, og markerer
   usikre eller manglende felt med «Kontroller».
6. **Korrigering** – brukeren korrigerer feil eller mangler i forslagene.
7. **Bokføring** – brukeren lagrer de bekreftede verdiene og bokfører bilaget.
8. **Logout** – brukeren logger ut, og sesjonen tilbakekalles.
9. **Login igjen** – brukeren logger inn på nytt og ser det bokførte bilaget.

## Kriterier

Hvert punkt må være oppfylt før release:

### Identitet og sesjon
- [ ] Registrering med e-post og passord fungerer.
- [ ] Magic link fungerer som alternativ innlogging.
- [ ] Glemt passord / nullstilling fungerer.
- [ ] Sikker passordendring fungerer.
- [ ] Utlogging tilbakekaller sesjonen.
- [ ] Innlogging etter utlogging fungerer uten manuell inngripen.
- [ ] `HttpOnly`-cookie og CSRF-token er i bruk; ingen rå tokens i localStorage.

### Farm og tenant-isolasjon
- [ ] Brukeren kan opprette en Farm under onboarding.
- [ ] `/api/me` returnerer aktiv Farm med entitlements.
- [ ] Bilagruter er beskyttet av Farm-medlemskap og permission.
- [ ] En bruker uten medlemskap i en Farm kan ikke lese eller skrive bilag i den Farmen.

### Bilagsflyt
- [ ] Opplasting av PDF og bilde fungerer (maks 15 MB).
- [ ] Behandlingsstatus vises under OCR.
- [ ] Dokumentet vises side ved side med skjemaet på desktop.
- [ ] OCR-forslag vises i redigerbare felt.
- [ ] Usikre eller manglende forslag markeres med «Kontroller».
- [ ] Brukeren kan korrigere alle felt.
- [ ] «Lagre verdier» persistérer brukerbekreftede verdier via PATCH.
- [ ] «Bokfør bilag» oppretter en transaksjon og setter status til «ført».
- [ ] Suksess-state vises tydelig etter bokføring.
- [ ] Dobbeltinnsending er forhindret (knapper deaktiveres under prosessering).

### Release-gate
- [ ] Reisen over kan gjennomføres i staging uten manuell database- eller utviklerinngripen.
- [ ] Ingen kjente blokkerende feil i kjernereisen.
- [ ] Smoke tests (se `docs/SMOKE_TESTS.md`) er kjørt og bestått.

## Kjente begrensninger ved release

- Rate limiting er in-memory per instans og tilbakestilles ved restart/skalering.
- OCR har begrensninger (se `docs/STAGING_SETUP.md`).
- Barebonde er foreløpig ikke et komplett regnskapssystem.
- EHF, Peppol, Altinn, MVA-innsending, betaling, bankintegrasjon og komplett
  hovedbok er ikke implementert.