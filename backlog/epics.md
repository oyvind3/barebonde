# Product Backlog

## Epic 1: Identitet og tilgang

### Mål
Brukere skal kunne logge sikkert inn og administrere tilgang.

### User Stories

#### US-1.1: Registrering med e-postbekreftelse
**Som** ny bruker  
**Ønsker jeg** å registrere meg med e-post  
**Slik at** jeg kan få tilgang til plattformen

**Akseptkriterier:**
```gherkin
Gitt at jeg er på registreringssiden
Når jeg fyller inn gyldig e-post, navn og telefonnummer
Og klikker "Send bekreftelseslenke"
Så skal jeg motta en e-post med engangslenke
Og lenken skal utløpe etter 15 minutter
Og jeg skal ikke kunne bruke samme lenke twice
```

#### US-1.2: Innlogging med magic link
**Som** registrert bruker  
**Ønsker jeg** å logge inn med en e-postlenke  
**Slik at** jeg slipper å huske passord

**Akseptkriterier:**
```gherkin
Gitt at jeg har en registrert konto
Når jeg ber om innloggingslenke
Så skal jeg motta e-post innen 30 sekunder
Og lenken skal føre meg direkte til dashboardet
Og gamle lenker skal automatisk ugyldiggjøres
```

#### US-1.3: Rate limiting for auth-endpoints
**Som** systemadministrator  
**Ønsker jeg** rate limiting på autentisering  
**Slik at** vi beskytter mot brute force-angrep

**Akseptkriterier:**
```gherkin
Gitt at en IP-adresse sender forespørsler
Når mer enn 5 registerforespørsler sendes på 1 minutt
Så skal ytterligere forespørsler returnere 429 Too Many Requests
Og brukeren skal få beskjed om når de kan prøve igjen
Og legitime brukere skal ikke påvirkes
```

### Pågående sak: profil ved onboarding

- [x] Lagre navn, e-post, adresse og E.164-telefonnummer i Cosmos ved e-postverifisert onboarding.
- [x] Del onboarding i korte steg for foretak, drift, personlig profil og betaling, og lagre strukturerte gårdsvalg for senere tilpasning.
- [x] Bekreft e-post med engangslenke før betalingsvalg og gårdsopprettelse.
- [x] Fyll inn og lagre BRREG-adresse, postnummer og poststed for valgt foretak.
- [x] Etabler serverstyrte sesjoner og autoritativ FarmUser-tilknytning etter Cosmos-bootstrap-fasen.
- [x] Implementer rate limiting på alle auth-endpoints

Teknisk merknad: Bransje, selskapsform og registrert adresse hentes fra BRREG når foretaket velges. Drifts- og modulvalg lagres på gårdsprofilen i Cosmos. Onboardingkladden i nettleseren er bare UX-støtte til e-postlenken; sesjonen og FarmUser er autoritative i backend.

---

## Epic 2: Gårdsprofil og virksomhetsoversikt

### Mål
Gi bonden en samlet oversikt over gården.

### User Stories

#### US-2.1: Opprette gård
**Som** bonde  
**Ønsker jeg** å registrere gården min  
**Slik at** jeg kan administrere den digitalt

**Akseptkriterier:**
```gherkin
Gitt at jeg er innlogget og har verifisert e-post
Når jeg oppretter en ny gård
Og legger til organisasjonsnummer
Så skal gårdsdata hentes automatisk fra BRREG
Og jeg skal kunne bekrefte eller korrigere informasjonen
Og gården skal knyttes til min bruker som eier
```

#### US-2.2: Flere brukere per gård
**Som** gårdeier  
**Ønsker jeg** å invitere familiemedlemmer  
**Slik at** vi kan samarbeide om driften

**Akseptkriterier:**
```gherkin
Gitt at jeg er eier av en gård
Når jeg inviterer en ny bruker med e-post
Og definerer deres rolle (medeier, ansatt, rådgiver)
Så skal de motta en invitasjon på e-post
Og de skal få riktige tilganger når de aksepterer
```

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

### User Stories

#### US-3.1: Laste opp dokumenter
**Som** bonde  
**Ønsker jeg** å laste opp dokumenter  
**Slik at** jeg har dem samlet og trygge

**Akseptkriterier:**
```gherkin
Gitt at jeg er inne på en gård jeg har tilgang til
Når jeg drar og slipper en PDF-fil
Og velger kategori (faktura, avtale, sertifikat)
Så skal filen lastes opp innen 5 sekunder
Og jeg skal se en forhåndsvisning
Og filen skal være søkbar
```

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

### User Stories

#### US-4.1: Lage avtaler fra maler
**Som** bonde  
**Ønsker jeg** å bruke ferdige avtalemaler  
**Slik at** jeg sparer tid og unngår feil

**Akseptkriterier:**
```gherkin
Gitt at jeg trenger en leiekontrakt
Når jeg velger en mal fra biblioteket
Og fyller inn de nødvendige feltene
Så skal en komplett avtale genereres
Og jeg skal kunne sende den til signering
```

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

### User Stories

#### US-5.1: Sende faktura med EHF
**Som** bonde  
**Ønsker jeg** å sende fakturaer elektronisk  
**Slik at** kundene mine får dem raskt

**Akseptkriterier:**
```gherkin
Gitt at jeg har solgt varer/tjenester
Når jeg oppretter en ny faktura
Og legger til kunde og linjevarer
Så skal faktura beregne MVA automatisk
Og jeg skal kunne sende via EHF/Peppol
Og faktura skal arkiveres automatisk
```

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

### User Stories

#### US-6.1: Motta meldinger fra Landbruksdirektoratet
**Som** bonde  
**Ønsker jeg** å motta offentlige meldinger digitalt  
**Slik at** jeg ikke går glipp av frister

**Akseptkriterier:**
```gherkin
Gitt at jeg har en aktiv gård
Når Landbruksdirektoratet sender meg en melding
Så skal jeg motta varsel i appen og på e-post
Og meldingen skal arkiveres under gården
Og jeg skal kunne svare direkte
```

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

### User Stories

#### US-7.1: Registrere maskiner
**Som** bonde  
**Ønsker jeg** å registrere mine maskiner  
**Slik at** jeg har oversikt over verdiene mine

**Akseptkriterier:**
```gherkin
Gitt at jeg kjøper en ny traktor
Når jeg registrerer maskinen med serienummer
Og legger til kjøpsdato og pris
Så skal maskinen vises i oversikten
Og jeg skal kunne legge til bilder og dokumenter
Og avskriving skal beregnes automatisk
```

Mulige funksjoner:
- Maskiner
- Vedlikehold
- Servicehistorikk
- Kostnader

---

## Epic 8: Drift og planlegging

### Mål
Støtte daglig drift.

### User Stories

#### US-8.1: Oppgaveliste for sesongen
**Som** bonde  
**Ønsker jeg** å lage en oppgaveliste  
**Slik at** jeg holder oversikt over hva som må gjøres

**Akseptkriterier:**
```gherkin
Gitt at vårsesongen nærmer seg
Når jeg oppretter oppgaver (gjødsling, såing, sprøyting)
Og setter frister og prioritet
Så skal jeg få varsler før forfall
Og jeg skal kunne markere oppgaver som fullført
Og historikk skal bevares for neste år
```

Mulige funksjoner:
- Oppgaver
- Kalender
- Sesongplanlegging
- Frister

---

## Tekniske Krav (Gjelder alle epics)

### Sikkerhet
- Alle endpoints skal ha rate limiting
- Persondata skal krypteres i hvile og transit
- Logging skal ikke inkludere sensitive data

### Ytelse
- Sideinnlasting < 3 sekunder på 3G
- API-respons < 500ms for 95% av forespørsler
- Støtt minst 100 samtidige brukere

### Tilgjengelighet
- WCAG 2.1 AA nivå
- Tastaturnavigasjon
- Skjermleserstøtte

### Mobil
- Responsiv design for alle skjermer
- Touch targets minimum 44x44px
- Testet på iOS og Android nettlesere
