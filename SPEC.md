# Leads Dashboard — specyfikacja zgodna z leadpipe T0

## Cel

Dashboard ma być panelem operacyjnym nad istniejącą implementacją `leadpipe` z repo `/tmp/leadpipe-t0/`. Nie duplikuje logiki pipeline i nie zakłada osobnego systemu CRM. Źródłem prawdy dla Phase 1 jest kod `leadpipe`, jego modele Pydantic, rulesety YAML oraz plik `.leadpipe/state.json`.

## Co faktycznie istnieje w leadpipe

Pipeline działa lokalnie jako moduły Python i CLI:

```text
CSV import
  -> Lead Pydantic
  -> T0 scan: DNS, HTTP, SSL, HTML, tech, performance
  -> T0.5 enrichment: NIP, REGON/VAT best-effort, cache opcjonalny
  -> T1 parse: JSON-LD, kontakt, formularze, CTA, industry fit
  -> DecisionEngine: YAML rules -> CampaignDecision + DecisionTrace
  -> .leadpipe/state.json
```

CLI udostępnia cztery komendy:

- `leadpipe import <file>` - waliduje CSV przez `ImportCsvSchema`, tworzy `Lead` i zapisuje do state.
- `leadpipe scan <selector>` - dla `batch` albo konkretnego `lead_id` uruchamia T0, T0.5 i T1, zapisuje `scans`.
- `leadpipe decide <selector>` - scala sygnały ze skanów, uruchamia `DecisionEngine`, zapisuje `decisions`.
- `leadpipe pipeline <batch_size> [--file <file>]` - importuje opcjonalny CSV, skanuje batch i zapisuje decyzje.

Stan CLI jest plikowy:

```json
{
  "leads": [],
  "scans": {
    "<lead_id>": {
      "t0": {},
      "t0_5": {},
      "t1": {}
    }
  },
  "decisions": {
    "<lead_id>": {
      "decision": {},
      "trace": {}
    }
  }
}
```

Ścieżka domyślna to `.leadpipe/state.json`, z możliwością nadpisania przez `LEADPIPE_STATE`.

## Stack dashboardu

- Frontend: React 19, TypeScript, Vite, Tailwind CSS, shadcn/ui, TanStack Table, TanStack Query, React Router, Recharts.
- Backend Phase 1: lekki wrapper Python wokół `leadpipe`.
- Backend może być FastAPI albo Flask, ale jego rola jest ograniczona: czyta `state.json`, waliduje dane modelami `leadpipe.models`, wywołuje funkcje lub komendy CLI i zwraca JSON dla UI.
- Brak własnych modeli domenowych dla leadów, decyzji i trace. API używa kontraktów z `leadpipe`: `Lead`, `CampaignDecision`, `DecisionTrace`, `ScoreBreakdown`, `RuleEvaluation`, `ImportCsvSchema`, `FeedbackCsvSchema`.

## Czego Phase 1 nie zakłada

Te elementy nie istnieją w obecnym kodzie leadpipe T0 i nie mogą być opisane jako gotowy backend dashboardu:

- FastAPI + Postgres jako źródło prawdy.
- Alembic i migracje produkcyjnej bazy.
- CX webhook/importer jako część dashboardu.
- CEO inbox i outreach jako gotowe workflow.
- Scraper ops, start/stop scraperów i log tail.
- T2 Vision, copywriter queue, outbox i feedback automation.

Te pomysły zostają jako **Phase 2 / Future scope** po pojawieniu się odpowiedniego kodu w leadpipe.

## Widoki i trasy

### `/` albo `/leads` — Lead list

Tabela czytana ze `state.json`.

Kolumny:

- ID
- Domain / normalized_domain
- Company
- NIP
- Source
- Status: `new`, `scanned`, `decided`, `exported`, `suppressed`, `skipped`
- T0 confidence
- T1 campaign confidence
- Decision action
- Campaign
- Rule key
- Created

Akcje:

- import CSV
- scan selected lead albo batch
- decide selected lead albo batch
- run pipeline dla CSV/batch size

### `/lead/:id` — Lead detail

Sekcje:

- `Lead` z modelu Pydantic.
- T0: DNS, HTTP, SSL, HTML, tech, performance oraz sygnały, np. `domain_present`, `https_missing`, `viewport_missing`, `wordpress_detected`, `speed_slow`.
- T0.5: enrichment, `nip_present`, `regon_present`, `vat_active`, `company_confirmed`.
- T1: JSON-LD, kontakty, formularze, CTA, industry, sygnały `contactability`, `industry_fit`, `lead_value`, `competitor`.
- Decision: `CampaignDecision`, `DecisionTrace`, evaluated rules, winning rule, blocked_by, score breakdown.

### `/pipeline` — Pipeline view

Wizualizacja obecnego stanu:

```text
Imported/New -> Scanned/T0+T0.5+T1 -> Decided -> Exported/Future
```

Panel pokazuje liczbę leadów per status, błędy skanowania, brakujące decyzje oraz rozkład kampanii.

### `/rulesets` — Rulesety YAML

Read-only w Batch 1-4, edycja w Batch 5.

Pliki:

- `leadpipe/rules/decision_gates.yml`
- `leadpipe/rules/campaigns.yml`
- `leadpipe/rules/evidence.yml`
- `leadpipe/rules/suppression.yml`
- `leadpipe/rules/t2_eligibility.yml`
- `leadpipe/rules/feedback.yml`

Kampanie z `CampaignKey`:

- `REDESIGN_OUTDATED`
- `REDESIGN_ADS_WASTE`
- `REDESIGN_CONVERSION`
- `REDESIGN_TRUST`
- `WORDPRESS_REWORK`
- `MOBILE_REBUILD`
- `TECH_REBUILD`

## API Phase 1

Endpointy mają odpowiadać istniejącym funkcjom CLI:

- `GET /api/state` - surowy albo zwalidowany snapshot `.leadpipe/state.json`.
- `GET /api/leads` - lista `Lead` z agregatami `scans` i `decisions`.
- `GET /api/leads/{id}` - detail leadu ze skanami i decyzją.
- `POST /api/import` - przyjmuje CSV zgodny z `ImportCsvSchema`, wywołuje `leadpipe import` albo `command_import`.
- `POST /api/scan` - `{ "selector": "batch" | "<lead_id>" }`, wywołuje `leadpipe scan`.
- `POST /api/decide` - `{ "selector": "batch" | "<lead_id>" }`, wywołuje `leadpipe decide`.
- `POST /api/pipeline` - `{ "batchSize": number, "file"?: string }`, wywołuje `leadpipe pipeline`.
- `GET /api/rulesets` - lista plików YAML i wersji rulesetu.
- `GET /api/rulesets/{name}` - treść rulesetu.

Backend może wywoływać bezpośrednio funkcje z `leadpipe.cli` albo proces CLI. W obu wariantach nie wolno przepisywać T0/T0.5/T1 ani `DecisionEngine` w dashboardzie.

## CSV

Import CSV jest zgodny z `ImportCsvSchema`:

- `domain` wymagane
- `url`
- `company_name`
- `nip`
- `source`
- `contact_email`
- `notes`

Feedback CSV istnieje w kodzie jako `FeedbackCsvSchema`, ale Phase 1 dashboardu nie implementuje jeszcze automatycznego feedback loop. Pola:

- `domain`
- `email`
- `event`
- `timestamp`
- `notes`

## Auth i deploy

- Authelia pozostaje warstwą SSO za Caddy.
- Frontend może być hostowany statycznie na `leads.luxewor.duckdns.org`.
- `/api/*` reverse proxy do lekkiego backendu wrappera.
- Backend musi mieć ustawione `LEADPIPE_STATE` i dostęp do instalacji/modułu `leadpipe`.

## Future scope

- Persistencja Postgres oparta o `leadpipe/db_schema.py`, jeśli leadpipe zacznie jej realnie używać w CLI/API.
- CX importer i mapowanie leadów z web form.
- CEO inbox, manual QA workflow i audit override.
- Scraper ops.
- T2 Vision, copywriter, outreach, suppression UI i feedback automation.
