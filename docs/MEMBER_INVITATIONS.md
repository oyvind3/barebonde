# Medlemsinvitasjoner

Invitasjoner ligger i `farm_invitations`, partisjonert på `/farm_id`. Dokument-ID-en er en formålsseparert HMAC av Farm-ID og normalisert e-post. En invitasjon er ikke et `FarmUser`-medlemskap og gir ingen tilgang før den aksepteres.

Et tilfeldig token finnes kun i e-postlenken. Cosmos lagrer bare en HMAC-hash. `GET /api/invitations/verify` validerer lenken uten sideeffekt og erstatter tokenet med et signert completion-intent. Accept og decline krever sesjon, CSRF, verifisert e-post og at e-posten matcher invitasjonen.

Owner kan invitere `manager` eller `staff`, se invitasjoner, sende på nytt og trekke tilbake. Resend har serverlagret cooldown og roterer token først etter at Plunk har akseptert e-posten. Leveringsstatus er separat fra invitasjonens livssyklus (`pending`, `accepted`, `declined`, `revoked`).

Nye brukere opprettes aldri av invitasjonen; de registrerer og verifiserer e-post før de eksplisitt aksepterer. Produksjon krever at `farm_invitations` opprettes via det manuelle Cosmos-bootstrap-skriptet. Fase 7C med rolleadministrasjon og eierskapsoverføring er ikke del av denne funksjonen.
