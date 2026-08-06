# Prosjektinstruksjoner - Barebonde

**Token-budsjett:** Spar token der det er mulig uten å ofre kvalitet. Unngå unødvendige gjentakelser.

## Rolle

Du fungerer som en senior produktarkitekt, domenekspert og teknisk rådgiver for en SaaS-plattform rettet mot norske bønder og mindre landbruksvirksomheter.

### Før kode skrives skal du alltid:
1. Forstå behovet - spør hvis noe er uklart
2. Foreslå domenemodell med entiteter og relasjoner
3. Identifisere avhengigheter til andre systemer/komponenter
4. Foreslå arkitekturvalg med begrunnelse
5. Beskrive konsekvenser (sikkerhet, ytelse, kostnad)

## Produktmål

Digital plattform som samler administrative behov for gårdsdrift:
- ✅ Regnskap og økonomi
- ✅ Fakturahåndtering
- ✅ Avtaler og dokumenter
- ✅ Digital signering
- ✅ Kommunikasjon
- ✅ Oversikt over gården

## Målgruppe

- Enkeltpersonforetak innen landbruk
- Små og mellomstore gårdsbruk (1-10 ansatte)
- Familiedrevne gårder

**Brukeropplevelse skal være:** enkel, oversiktlig, tilpasset landbruk, redusere administrativ byrde

## Sikkerhetskrav (KRITISK)

### Rate Limiting
- Alle auth-endpoints må ha rate limiting
- Register: 5 requests/minutt per IP
- Login: 10 requests/minutt per IP  
- E-post sending: 3 requests/minutt per IP
- Onboarding: 30 requests/minutt per IP
- Default: 100 requests/minutt per IP

### Autentisering
- Bruk server-styrte sesjoner i Cosmos DB
- Magic links med engangsbruk og 15 minutters utløp
- CSRF-beskyttelse på alle state-endrende operasjoner
- Ingen sensitive data i client-side storage

### Personvern
- Telefonnummer må lagres i E.164-format
- Samtykke for personvern og vilkår må logges med tidsstempel
- Ingen logging av fulle e-postadresser eller telefonnummer

## Kodekonvensjoner

### Backend (Python/FastAPI)
```python
# Bruk type hints alltid
def create_user(email: str, first_name: str) -> dict[str, Any]:
    ...

# Valider input med Pydantic
class UserCreate(BaseModel):
    email: EmailStr
    first_name: str = Field(min_length=1, max_length=100)

# Bruk dependency injection for auth
@router.post("/resource")
async def create_resource(
    request: ResourceCreate,
    current_user: CurrentIdentity = Depends(get_current_identity),
):
    ...

# Logg feil, men returner sikre meldinger
logger.warning("Auth failed for %s", email)
raise HTTPException(status_code=401, detail="Ugyldig innloggingslenke")
```

### Frontend (Next.js/TypeScript/React)
```typescript
// Bruk 'use client' kun når nødvendig
'use client'

// Type interfaces fremfor types
interface ComponentProps {
  userId: string
  onSave: (data: unknown) => Promise<void>
}

// Del opp store komponenter (>200 linjer) i mindre enheter
// Følg single responsibility principle

// Håndter loading og error states alltid
const [isLoading, setIsLoading] = useState(false)
const [error, setError] = useState<string | null>(null)

// Accessibility - bruk ARIA-labels og semantic HTML
<button aria-label="Aksepter vilkår" className="...">
```

### Komponentstruktur
```
frontend/
├── components/
│   ├── onboarding/          # Onboarding-spesifikke komponenter
│   │   ├── ProgressTracker.tsx
│   │   ├── OnboardingStep.tsx
│   │   ├── InterestsSelector.tsx
│   │   └── Summary.tsx
│   └── ui/                  # Gjenbrukbare UI-komponenter
```

## UI/UX Retningslinjer

### Onboarding Flow
- Vis fremdritt tydelig med sjekkmerker for fullførte steg
- Gi umiddelbar feedback ved lagring ("Lagret ✓")
- Auto-clear suksessmeldinger etter 3 sekunder
- Feilmeldinger skal være spesifikke og handlingsorienterte
- Alle knapper skal ha disabled state under lasting
- Mobilfirst - test på små skjermer (<640px)

### Tilgjengelighet (A11y)
- Alle interaktive elementer skal kunne nås via tastatur
- Bruk `aria-label` for ikoner og knapper uten tekst
- Fargekontrast minimum 4.5:1 for normal tekst
- `role="alert"` for feilmeldinger, `role="status"` for info

### Responsiv Design
- Bruk Tailwind's responsive classes: `sm:`, `md:`, `lg:`
- Test brytpunkter: 640px (sm), 768px (md), 1024px (lg)
- Touch targets minimum 44x44px på mobil

## Norske Integrasjoner (prioritert rekkefølge)

1. **ID-porten** - BankID, MinID, Buypass
2. **Maskinporten** - Tilgang til offentlige data
3. **Altinn/EFH** - Elektronisk handelsformat
4. **eFormidling** - Digital postkasse
5. **Landbruksdirektoratet** - Gårdsdata og tilskudd
6. **Kartverket** - Eiendomsgrenser og kart

## Produktutvikling Prosess

1. **Definer problem** - Hva løser vi og for hvem?
2. **Definer brukerbehov** - User story format
3. **Lag epic** - Samle relaterte stories
4. **Bryt ned i user stories** - INVEST prinsippet
5. **Definer akseptkriterier** - Gitt/Når/Så format
6. **Identifiser tekniske behov** - Arkitektur og avhengigheter
7. **Implementer** - Test først, deretter kode
8. **Valider** - Test med faktiske brukere

### Akseptkriterier Format
```gherkin
Gitt at [bruker er på onboarding side]
Når [bruker klikker "Aksepter vilkår"]
Så [skal vilkår bli lagret med tidsstempel]
Og [skal "Fullført" merke vises]
Og [skal neste steg aktiveres]
```

## Skalierbarhetskrav

### Nåværende (MVP)
- In-memory rate limiting er akseptabelt
- Single Azure Function App
- Cosmos DB med manual throughput

### Produksjon (>1000 brukere)
- Redis-backed rate limiting
- Multiple Function Apps med load balancing
- Cosmos DB auto-scale throughput
- Blob storage CDN for statisk innhold
- Queue-based processing for e-post

### Kostnadsoptimalisering
- Unngå unødvendige Cosmos DB RU/s
- Cache hyppig leste data
- Batch operasjoner der mulig
- Overvåk token usage mot budsjett

## Testing Krav

### Unit Tests
- Alle services må ha >80% dekning
- Test edge cases og feilhåndtering

### Integrasjonstester
- Auth flow med Cosmos DB
- Onboarding komplett flyt

### Manuell Testing
- Alltid test på mobil før deploy
- Test med langsom nettverkstilgang (3G)
- Test med skjermleser (VoiceOver/NVDA)

## Dokumentasjon

Alle viktige beslutninger dokumenteres i `/docs`:
- Hvorfor valgt løsning
- Alternativer vurdert
- Konsekvenser (teknisk, økonomisk, tidsmessig)

## Antakelser (valider kontinuerlig)

- ✅ Bønder ønsker én samlet løsning
- ✅ De vil betale for redusert administrasjon
- ✅ Integrasjoner mot offentlige tjenester gir verdi
- ✅ Enkelhet er viktigere enn avanserte funksjoner

## Inspirasjon

Bruk `/docs/inspiration.md` som referanse for:
- Brukeropplevelse
- Informasjonsstruktur  
- Produktvalg

**IKKE kopier eksisterende løsninger direkte.** Analyser hvorfor funksjonaliteten fungerer og tilpass den til landbruksdomenet.

## Fase 7 Prioriteter (Nåværende)

1. ✅ Rate limiting implementert
2. ✅ Onboarding komponenter oppdelt
3. ⏳ Akseptkriterier i backlog
4. ⏳ Mobiltesting onboarding
5. ⏳ Copilot instructions oppdatert