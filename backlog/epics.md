# Product Backlog

## Epic 1: Identitet og tilgang

### Mål
Brukere skal kunne logge sikkert inn og administrere tilgang.

Mulige funksjoner:
- Innlogging via e-postlenke
- Serverstyrte sesjoner
- Roller og rettigheter
- Flere brukere per gård

### Pågående sak: profil ved onboarding

- [x] Lagre navn, e-post, adresse og E.164-telefonnummer i Cosmos ved e-postverifisert onboarding.
- [x] Del onboarding i korte steg for foretak, drift, personlig profil og betaling, og lagre strukturerte gårdsvalg for senere tilpasning.
- [x] Bekreft e-post med engangslenke før betalingsvalg og gårdsopprettelse.
- [x] Fyll inn og lagre BRREG-adresse, postnummer og poststed for valgt foretak.
- [x] Etabler serverstyrte sesjoner og autoritativ FarmUser-tilknytning etter Cosmos-bootstrap-fasen.

Teknisk merknad: Bransje, selskapsform og registrert adresse hentes fra BRREG når foretaket velges. Drifts- og modulvalg lagres på gårdsprofilen i Cosmos. Onboardingkladden i nettleseren er bare UX-støtte til e-postlenken; sesjonen og FarmUser er autoritative i backend.

---

## Epic 2: Gårdsprofil og virksomhetsoversikt

### Mål
Gi bonden en samlet oversikt over gården.

Mulige funksjoner:
- Opprette gård
- Organisasjonsinformasjon
- Eiendomsinformasjon
- Kontaktinformasjon
- Oversikt over ressurser

---

## Epic 3: Dokumenthåndtering

### Mål
Samle viktige dokumenter på ett sted.

Mulige funksjoner:
- Laste opp dokumenter
- Kategorisering
- Søking
- Dokumenthistorikk

Dokumenttyper:
- Avtaler
- Faktura
- Forsikring
- Sertifikater
- Offentlige dokumenter

---

## Epic 4: Avtalehåndtering

### Mål
Forenkle håndtering av avtaler.

Mulige funksjoner:
- Lage avtaler
- Maler
- Frister
- Varslinger
- Digital signering

Integrasjon:
- eSignering

---

## Epic 5: Faktura og økonomi

### Mål
Forenkle økonomiadministrasjon.

Mulige funksjoner:
- Motta faktura
- Sende faktura
- EHF
- Fakturaoversikt
- Kostnadsanalyse

Integrasjoner:
- Peppol
- ELMA
- Regnskapssystemer

---

## Epic 6: Kommunikasjon med offentlige tjenester

### Mål
Samle offentlig kommunikasjon.

Mulige funksjoner:
- Motta meldinger
- Varslinger
- Arkivering

Integrasjoner:
- eFormidling
- Digital postkasse

---

## Epic 7: Maskin- og ressursoversikt

### Mål
Ha kontroll på gårdens verdier.

Mulige funksjoner:
- Maskiner
- Vedlikehold
- Servicehistorikk
- Kostnader

---

## Epic 8: Drift og planlegging

### Mål
Støtte daglig drift.

Mulige funksjoner:
- Oppgaver
- Kalender
- Sesongplanlegging
- Frister
