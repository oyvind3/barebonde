# Cosmos-bootstrap

Cosmos-ressurser opprettes og valideres bare med det manuelle skriptet `backend/scripts/bootstrap_cosmos.py`. Function App-start og GitHub Actions kjører aldri bootstrap.

Kjør fra repository-roten med de vanlige backend-miljøvariablene satt lokalt:

```bash
python backend/scripts/bootstrap_cosmos.py --dry-run
```

`--dry-run` kobler til Cosmos, leser metadata og viser manglende ressurser eller partisjonsnøkkelkonflikter uten å opprette noe. `--validate-only` feiler dersom en database eller container mangler. Uten flagg opprettes bare manglende database og containere; eksisterende containere blir kun validert.

`--database-id <id>` overstyrer database-ID for én kjøring. Skriptet skriver aldri connection string eller credentials, og det sletter, erstatter, migrerer eller endrer aldri throughput eller data. Kjør ikke mot produksjon uten en uttrykkelig operasjonell beslutning.

Den autoritative containerlisten og partisjonsnøklene ligger i `backend/app/db/cosmos_schema.py`. `subscription_usage` inngår bevisst ikke før usage-modulen er implementert.
