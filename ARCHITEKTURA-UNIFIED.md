# Architektura Unified — Leads Dashboard + leadpipe

**Data:** 2026-05-27  
**Zakres:** dashboard nad rzeczywistym `leadpipe` T0 z repo `/tmp/leadpipe-t0/`.

## 1. Korekta założeń

Poprzednie plany opisywały docelowy MeNET Ops Center z Postgresem, CX importerem, scraper ops, CEO inbox, T2 Vision, copywriterem i outreach. To zostaje jako kierunek **Phase 2 / Future scope**.

Aktualny kod leadpipe implementuje mniejszy, ale konkretny rdzeń:

- modele Pydantic;
- CSV import;
- T0 scan;
- T0.5 enrichment;
- T1 parser;
- `DecisionEngine`;
- rulesety YAML;
- CLI;
- plikowy state `.leadpipe/state.json`.

Dashboard ma najpierw pokazać i obsłużyć ten rdzeń.

## 2. Integracja z leadpipe

Dashboard korzysta z kodu leadpipe bez duplikowania logiki.

```text
Dashboard UI
  -> backend wrapper Python
  -> leadpipe CLI/API
  -> .leadpipe/state.json
  -> leadpipe.t0 / leadpipe.t0_5 / leadpipe.t1
  -> DecisionEngine
  -> leadpipe/rules/*.yml
```

### Backend wrapper

Wrapper może działać w dwóch trybach:

- import modułów Python i wywołanie funkcji z `leadpipe`;
- uruchomienie komend CLI `leadpipe import`, `leadpipe scan`, `leadpipe decide`, `leadpipe pipeline`.

Preferowany jest import modułów, bo ułatwia walidację Pydantic i testy. CLI pozostaje kontraktem funkcjonalnym, do którego endpointy API mają być dopasowane.

### State

Dashboard czyta i pokazuje:

- `leads[]` jako modele `Lead`;
- `scans[lead_id].t0`;
- `scans[lead_id].t0_5`;
- `scans[lead_id].t1`;
- `decisions[lead_id].decision`;
- `decisions[lead_id].trace`.

Nie tworzymy drugiego magazynu prawdy w Phase 1.

## 3. Pipeline w dashboardzie

```text
CSV import
  -> Lead(status=new)
  -> scan
      -> T0: DNS/HTTP/SSL/HTML/tech/performance
      -> T0.5: NIP/REGON/VAT enrichment
      -> T1: JSON-LD/contact/forms/CTA/industry
      -> Lead(status=scanned)
  -> decide
      -> DecisionEngine + YAML rules
      -> CampaignDecision + DecisionTrace
      -> Lead(status=decided)
```

UI pokazuje:

- batch/listę leadów z pliku state;
- sygnały T0/T0.5/T1;
- decyzje engine;
- trace reguł;
- rulesety YAML.

## 4. Modele i kontrakty

Modele dashboardu muszą bazować na `leadpipe.models`:

- `Lead`
- `LeadStatus`
- `CampaignDecision`
- `DecisionAction`
- `CampaignKey`
- `DecisionTrace`
- `RuleEvaluation`
- `ScoreBreakdown`
- `Batch`

CSV:

- import: `ImportCsvSchema`;
- feedback: `FeedbackCsvSchema` jako kontrakt przyszły.

Własne DTO są dopuszczalne tylko jako modele widokowe, np. `LeadListRow`, i muszą być budowane z danych leadpipe.

## 5. Rulesety

Aktywne pliki:

- `decision_gates.yml`
- `campaigns.yml`
- `evidence.yml`
- `suppression.yml`
- `t2_eligibility.yml`
- `feedback.yml`

Kampanie:

- `REDESIGN_OUTDATED`
- `REDESIGN_ADS_WASTE`
- `REDESIGN_CONVERSION`
- `REDESIGN_TRUST`
- `WORDPRESS_REWORK`
- `MOBILE_REBUILD`
- `TECH_REBUILD`

Dashboard w pierwszych batchach pokazuje rulesety read-only. Edycja YAML wymaga walidacji i dry-run przez `DecisionEngine`.

## 6. API Phase 1

Endpointy odpowiadają CLI:

- `GET /api/state`
- `GET /api/leads`
- `GET /api/leads/{id}`
- `POST /api/import`
- `POST /api/scan`
- `POST /api/decide`
- `POST /api/pipeline`
- `GET /api/rulesets`
- `GET /api/rulesets/{name}`

Nie dodajemy w Phase 1 endpointów:

- `/api/ceo/*`
- `/api/scraper/*`
- `/api/copywriter/*`
- `/api/outreach/*`
- `/api/import/cx/*`

## 7. Deployment

```text
Browser
  -> leads.luxewor.duckdns.org albo ops.luxewor.duckdns.org
  -> Caddy + Authelia
  -> static React/Vite
  -> /api/* reverse proxy
  -> backend wrapper
  -> leadpipe checkout/package + LEADPIPE_STATE
```

Wymagane ustawienia:

- `LEADPIPE_STATE=/path/to/.leadpipe/state.json`
- dostęp backendu do pakietu `leadpipe`
- read/write do katalogu `.leadpipe`
- read do `leadpipe/rules`

## 8. Future scope

Nie usuwamy wcześniejszych pomysłów, ale oznaczamy je jako późniejsze:

- Postgres i Alembic z `leadpipe/db_schema.py`.
- CX webhook/importer.
- Self-Evolving Core read-only integration.
- Scraper ops.
- CEO Command Center.
- Copywriter Queue.
- Outreach i feedback loop.
- T2 Vision execution.

Te moduły nie są częścią obecnego leadpipe T0, więc dokumentacja Phase 1 nie może traktować ich jako istniejącego kontraktu.
