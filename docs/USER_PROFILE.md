# Brukerprofil

Brukerprofilen følger den interne User-identiteten på tvers av Farms. `GET` og `PATCH /api/profile` bruker serverstyrt sesjon og CSRF for mutasjoner. E-post, status og intern bruker-ID er skrivebeskyttet; e-postendring krever senere verifiseringsflyt.

Vilkår og personvern lagres med versjon og tidspunkt. Profilstatus beregnes på serveren fra navn og aksepterte dokumenter.
