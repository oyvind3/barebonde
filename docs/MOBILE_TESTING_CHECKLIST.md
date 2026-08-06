# Mobiltesting Sjekkliste - Onboarding

## Testenheter som må dekkes

### iOS
- [ ] iPhone SE (4.7") - 375x667px
- [ ] iPhone 12/13 (6.1") - 390x844px
- [ ] iPhone Pro Max (6.7") - 428x926px
- [ ] Safari og Chrome

### Android
- [ ] Liten skjerm (5.0") - 360x640px
- [ ] Medium skjerm (6.0") - 412x915px
- [ ] Stor skjerm (6.5"+) - 412x892px
- [ ] Chrome, Samsung Internet, Firefox

## Onboarding Flow Tester

### 1. Sideinnlasting
- [ ] Siden lastes på under 3 sekunder på 4G
- [ ] Siden lastes på under 5 sekunder på 3G
- [ ] Loading state vises mens data hentes
- [ ] Ingen layout shift når innhold lastes

### 2. Progress Tracker
- [ ] Fremdriftsindikatoren er synlig uten scrolling på små skjermer
- [ ] Sjekkmerker for fullførte steg er tydelige (minimum 24x24px)
- [ ] Fargekontrast oppfyller WCAG AA (4.5:1)
- [ ] Screen leser kan lese fremdrift ("3 av 7 steg fullført, 43%")

### 3. Onboarding Steg
- [ ] Hvert steg har tilstrekkelig padding (minimum 16px)
- [ ] Tekst er lesbar uten zooming (minimum 16px for body)
- [ ] Lenker har minimum touch target 44x44px
- [ ] Knapper har tydelig disabled state

### 4. Personlig Profil (Steg 1)
- [ ] "Åpne profil" lenke er lett å trykke på
- [ ] "Aksepter vilkår" knapp er full bredde på mobil
- [ ] Feedback "Lagret ✓" vises i minst 3 sekunder
- [ ] Feilmeldinger er lesbare og spesifikke

### 5. Virksomhet (Steg 2)
- [ ] "Opprett eller velg gård" lenke er tydelig
- [ ] Tilbakeknapp fungerer korrekt
- [ ] Navigasjon mellom sider er smooth

### 6. Gårdsinnstillinger (Steg 3)
- [ ] Skjemaer er enkelt å fylle ut på mobil
- [ ] Input felt har riktig type (tel, email, etc.)
- [ ] Keyboard åpnes med riktig layout

### 7. Bankkonto (Steg 4 - Valgfritt)
- [ ] Valgfrie steg er tydelig markert som "(valgfritt)"
- [ ] Bruker kan hoppe over uten feil

### 8. Interesser (Steg 5)
- [ ] Checkbox-es er store nok til touch (minimum 44x44px inkludert label)
- [ ] Hele kortet er klikkbart, ikke bare checkbox-en
- [ ] Grid layout fungerer på tvers og langs modus
- [ ] Lagringsfeedback vises umiddelbart
- [ ] Kan velge/davelge flere interesser raskt

### 9. Oppsummering
- [ ] Brukerinfo er lesbar
- [ ] Gårdsnavn vises korrekt
- [ ] Abonnementstatus er tydelig

### 10. Fullfør Knapp
- [ ] Knapp er disabled når krav ikke er oppfylt
- [ ] Knapp er full bredde på mobil (< 640px)
- [ ] Loading state viser "Fullfører..."
- [ ] Suksessmelding "🎉 Onboarding er fullført!" vises tydelig
- [ ] Redirect skjer automatisk etter fullføring

## Responsivitet

### Brytpunkter
- [ ] < 640px (sm) - Enkolumn layout
- [ ] 640px - 768px - Overgang
- [ ] 768px - 1024px (md) - To-kolonne der relevant
- [ ] > 1024px (lg) - Full desktop layout

### Orientering
- [ ] Portrettmodus fungerer perfekt
- [ ] Landskapsmodus er brukbart
- [ ] Rotering mellom modi bevarer state

## Tilgjengelighet (A11y)

### Screen Lesere
- [ ] VoiceOver (iOS) kan navigere hele flowet
- [ ] TalkBack (Android) fungerer korrekt
- [ ] Alle knapper har aria-labels
- [ ] Fremdrift har role="progressbar"
- [ ] Feilmeldinger har role="alert"
- [ ] Statusmeldinger har role="status"

### Tastatur
- [ ] Alle elementer kan nås med Tab
- [ ] Fokus-indikator er tydelig
- [ ] Enter aktiverer knapper
- [ ] Escape lukker modaler (hvis noen)

### Visuell
- [ ] Fargekontrast minimum 4.5:1 for tekst
- [ ] Fargekontrast minimum 3:1 for store elementer
- [ ] Ikke stol kun på farge for informasjon
- [ ] Tekst kan zoome til 200% uten tap av funksjon

## Ytelse

### Nettverk
- [ ] Test på 3G (1.5 Mbps): Side lastes < 5s
- [ ] Test på 4G (10 Mbps): Side lastes < 2s
- [ ] Offline: Vennlig feilmelding vises
- [ ] Treg respons: Loading states vises

### Bildeoptimalisering
- [ ] Ingen store bilder som senker lasting
- [ ] SVG ikoner brukes der mulig
- [ ] Lazy loading for ikke-kritiske ressurser

## Sikkerhet på Mobil

- [ ] Rate limiting fungerer fra mobilnettverk
- [ ] Sesjons-cookie har secure flag i produksjon
- [ ] Ingen sensitive data i localStorage
- [ ] Magic links utløper korrekt

## Testing Under Ulike Forhold

### Miljø
- [ ] Innendørs med svakt WiFi
- [ ] Utendørs med mobildata
- [ ] Bevegelse (gående/buss)
- [ ] Sterkt sollys (skjermlesbarhet)

### Batteri
- [ ] Appen bruker ikke unødvendig batteri
- [ ] Background refresh er deaktivert

## Kjente Problemer og Workarounds

| Problem | Enhet/Browser | Workaround | Status |
|---------|--------------|------------|--------|
|         |              |            |        |

## Testrapport Mal

```markdown
### Test Økt
**Dato:** YYYY-MM-DD  
**Tester:** Navn  
**Enheter testet:** Liste enheter

### Resultater
- **Bestått:** X av Y tester
- **Feil:** Z feil funnet
- **Kritiske:** W kritiske problemer

### Kritiske Funnelser
1. Beskrivelse av kritisk problem
   - Enhet: 
   - Gjenskaping:
   - Forventet:
   - Faktisk:

### Mindre Problemer
1. Liste mindre problemer

### Anbefalinger
1. Prioriterte forbedringer
```

## Godkjenningskriterier for Produksjon

Før onboarding deployes til produksjon må følgende være oppfylt:

- [ ] Alle kritiske tester bestått
- [ ] Ingen WCAG A-brudd
- [ ] Sideinnlasting < 3s på 4G for alle testsider
- [ ] Testet på minimum 3 forskjellige enheter
- [ ] Testet på både iOS og Android
- [ ] Rate limiting verifisert på mobilnettverk
- [ ] Screen reader testing fullført

---

*Sist oppdatert: Fase 7*  
*Neste review: Etter første produksjonsrelease*
