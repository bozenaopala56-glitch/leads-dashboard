# CODEX CLI BRIEF — Leads Dashboard nad leadpipe

> **Zadanie:** Buduj dashboard zgodny z faktycznym kodem `leadpipe` w `/tmp/leadpipe-t0/`.
> **Najważniejsza zasada:** nie wymyślaj backendu Postgres/CEO/scraper, jeśli nie ma go w aktualnym leadpipe. Opakuj działający CLI/state pipeline.
> **Język:** kod i komentarze po angielsku, dokumentacja po polsku.

## Zakres Phase 1

Dashboard obsługuje:

- import CSV;
- skan T0/T0.5/T1;
- decyzje `DecisionEngine`;
- podgląd `.leadpipe/state.json`;
- podgląd leadów, sygnałów, decyzji i trace;
- przegląd rulesetów YAML.

## Faktyczny leadpipe

Repo: `/tmp/leadpipe-t0/`

Istniejące elementy:

- `leadpipe/models.py` - Pydantic contracts.
- `leadpipe/csv_schemas.py` - `ImportCsvSchema`, `FeedbackCsvSchema`.
- `leadpipe/cli.py` - komendy `import`, `scan`, `decide`, `pipeline`.
- `leadpipe/t0/*` - DNS/HTTP/SSL/HTML/tech/performance.
- `leadpipe/t0_5/*` - NIP/VAT enrichment i cache.
- `leadpipe/t1/*` - JSON-LD, contact, forms, CTA, industry.
- `leadpipe/engine.py` - `DecisionEngine`.
- `leadpipe/rules/*.yml` - decision gates, campaigns, evidence, suppression, t2 eligibility, feedback.
- `.leadpipe/state.json` - storage CLI.

## Backend

Backend ma być cienkim wrapperem Python:

- FastAPI albo Flask;
- bez własnego Postgresa w Phase 1;
- bez Alembica w Phase 1;
- bez własnych modeli domenowych konkurujących z `leadpipe.models`;
- endpointy mapowane na CLI: import, scan, decide, pipeline.

Preferowane jest importowanie funkcji z `leadpipe`, ale można użyć CLI, jeśli to prostsze operacyjnie.

## Frontend

Stack:

- React 19;
- TypeScript;
- Vite;
- Tailwind;
- shadcn/ui;
- TanStack Query;
- TanStack Table;
- React Router.

Widoki:

- Lead list.
- Lead detail.
- Pipeline board.
- Ruleset browser/editor w późniejszym batchu.

## Nie implementuj jako Phase 1

Oznacz jako **Future scope**:

- CX webhook/importer;
- CEO inbox;
- scraper ops;
- T2 Vision execution;
- copywriter;
- outreach;
- feedback automation;
- Postgres jako główny storage.

## Kontrakt danych

Używaj:

- `Lead`
- `CampaignDecision`
- `DecisionTrace`
- `ScoreBreakdown`
- `RuleEvaluation`
- `ImportCsvSchema`
- `FeedbackCsvSchema`
- enumów `LeadStatus`, `DecisionAction`, `CampaignKey`

Jeśli frontend potrzebuje widokowego kształtu danych, zbuduj DTO z tych modeli i zachowaj oryginalne payloady w detail view.

## API Phase 1

- `GET /health`
- `GET /api/state`
- `GET /api/leads`
- `GET /api/leads/{id}`
- `POST /api/import`
- `POST /api/scan`
- `POST /api/decide`
- `POST /api/pipeline`
- `GET /api/rulesets`
- `GET /api/rulesets/{name}`

## Deploy

- Frontend statyczny za Caddy + Authelia.
- `/api/*` reverse proxy do wrappera.
- Backend z dostępem do pakietu `leadpipe`.
- `LEADPIPE_STATE` wskazuje plik state używany przez CLI.

## Kryterium poprawności

Po wykonaniu dashboard ma pokazywać to samo, co da się uzyskać z:

```bash
leadpipe import leads.csv
leadpipe scan batch
leadpipe decide <lead_id>
leadpipe pipeline 10 --file leads.csv
```

Jeśli UI i CLI pokazują różne dane, CLI i `state.json` wygrywają.
