# ARCH.md — architektura dashboardu zgodna z leadpipe T0

Data aktualizacji: 2026-05-27
Zakres: dashboard nad rzeczywistym kodem `leadpipe` w `/tmp/leadpipe-t0/`.

## 1. Decyzja w skrócie

Phase 1 dashboardu jest lekką aplikacją nad istniejącym `leadpipe`, a nie nowym systemem CRM.

Źródłem prawdy są:

- modele Pydantic w `leadpipe/models.py`;
- CLI w `leadpipe/cli.py`;
- moduły `leadpipe/t0`, `leadpipe/t0_5`, `leadpipe/t1`;
- `DecisionEngine` w `leadpipe/engine.py`;
- rulesety YAML w `leadpipe/rules/`;
- plik `.leadpipe/state.json`.

Backend dashboardu ma jedną odpowiedzialność: wystawić UI wygodny dostęp do tych elementów. Nie przepisuje reguł, nie buduje alternatywnego engine i nie utrzymuje własnego modelu leadów.

## 2. Architektura Phase 1

```text
Browser
  -> Caddy + Authelia
  -> statyczny frontend React/Vite
  -> /api/*
  -> lekki backend Python
  -> leadpipe CLI albo importowane funkcje
  -> .leadpipe/state.json
  -> leadpipe.t0 / leadpipe.t0_5 / leadpipe.t1
  -> DecisionEngine + YAML rules
```

Backend może być FastAPI albo Flask. FastAPI jest sensownym wyborem ze względu na Pydantic, ale nie oznacza to własnej bazy Postgres ani osobnego domain layer.

## 3. Integracja z leadpipe

### Opcja preferowana: import modułów

Backend importuje funkcje i modele:

- `leadpipe.cli._load_state`, `_save_state`, `command_import`, `command_scan`, `command_decide`, `command_pipeline`;
- `leadpipe.models.Lead`, `CampaignDecision`, `DecisionTrace`;
- `leadpipe.csv_schemas.ImportCsvSchema`, `FeedbackCsvSchema`;
- `leadpipe.engine.DecisionEngine`;
- `leadpipe.t0.run_t0_batch`;
- `leadpipe.t0_5.run_t0_5`;
- `leadpipe.t1.run_t1`.

Zaletą jest brak parsowania stdout i łatwiejsze testy.

### Opcja alternatywna: CLI wrapper

Backend uruchamia komendy:

- `leadpipe import <file>`
- `leadpipe scan <selector>`
- `leadpipe decide <selector>`
- `leadpipe pipeline <batch_size> --file <file>`

Zaletą jest ścisła zgodność z obecnym interfejsem użytkowym leadpipe. Wadą jest konieczność obsłużenia stdout/stderr i kodów wyjścia.

Obie opcje muszą korzystać z `LEADPIPE_STATE` i nie mogą mieć drugiego, niespójnego storage.

## 4. State model

`leadpipe.cli` zapisuje stan atomowo do `.leadpipe/state.json`.

Kształt:

```json
{
  "leads": [],
  "scans": {},
  "decisions": {}
}
```

`leads` zawiera serializowane modele `Lead`.
`scans[lead_id]` zawiera wyniki `t0`, `t0_5`, `t1`.
`decisions[lead_id]` zawiera `decision` oraz `trace`.

Dashboard powinien walidować `leads` przez `Lead.model_validate`. Błędne rekordy pokazujemy jako problem danych albo pomijamy zgodnie z zachowaniem CLI, ale nie naprawiamy ich ad hoc w UI.

## 5. Modele domenowe

Dashboard używa modeli z leadpipe:

- `Lead`, `LeadStatus`
- `Signal`, `Evidence`, `ScanResult`
- `CampaignDecision`, `DecisionAction`, `CampaignKey`
- `DecisionTrace`, `RuleEvaluation`, `ScoreBreakdown`
- `Batch`, `BatchStatus`
- `OutreachEvent`, `SuppressionEntry` jako kontrakty przyszłe, nie aktywny workflow Phase 1

Ważne ograniczenie: `StrictModel` ma `extra="forbid"`. API dashboardu nie powinno dopisywać pól do tych obiektów. Pola widokowe należy trzymać w osobnych DTO odpowiedzi, np. `LeadListRow`, budowanych z modeli leadpipe.

## 6. Pipeline

### T0

`compute_t0_signals(domain)` uruchamia:

- DNS: A/AAAA, MX, TXT;
- HTTP: status, final URL, HTTPS, redirecty, błędy przejściowe;
- SSL: ważność certyfikatu, issuer, expiry, hostname match;
- HTML: viewport, title/identity, formularze, CTA, ukryty kontakt, rozmiar HTML;
- Tech: WordPress, Joomla/Drupal, GTM, Meta Pixel, stare assety;
- Performance: TTFB, rozmiar, gzip, cache headers.

Wynik trafia do `scans[lead_id].t0` jako `signals` i `scan_result`.

### T0.5

`run_t0_5(lead, html_text)`:

- normalizuje i waliduje NIP;
- wyciąga NIP z HTML;
- robi best-effort lookup REGON/VAT;
- opcjonalnie korzysta z `EnrichmentCache`;
- zwraca `lead`, `enrichment`, `signals`.

Sygnały: `nip_present`, `regon_present`, `vat_active`, `company_confirmed`.

### T1

`run_t1(html_text, headers)` analizuje:

- JSON-LD i organizację;
- emaile, telefony, social links;
- formularze;
- CTA;
- branżę i konkurencyjność.

Sygnały obejmują m.in. `has_email`, `has_phone`, `contactability`, `industry_fit`, `lead_value`, `competitor`, `campaign_confidence`.

### DecisionEngine

`DecisionEngine.evaluate(lead, signals)`:

1. Ładuje wszystkie `*.yml` z `leadpipe/rules`.
2. Buduje kontekst z pól leada i sygnałów T0/T0.5/T1.
3. Sortuje reguły po `(priority, key)`.
4. Ewaluuję operatory `exists`, `missing`, `eq`, `neq`, `in`, `contains`, `gte`, `gt`, `lte`, `lt`.
5. Obsługuje combine `and`, `or`, `weighted`.
6. Zwraca `CampaignDecision` oraz `DecisionTrace`.

Decyzje: `skip`, `retry`, `manual_review`, `t2_required`, `t2_optional`, `send`.

## 7. Rulesety

Rulesety istnieją jako YAML:

- `decision_gates.yml` - compliance, quality, country/industry fit, retry, contactability, manual QA.
- `campaigns.yml` - 7 kampanii WWW-first.
- `evidence.yml` - fallback/manual review dla dowodów.
- `suppression.yml` - hard bounce, active customer, cooldown.
- `t2_eligibility.yml` - decyzje o potrzebie T2, mimo że T2 nie jest jeszcze modułem wykonawczym w tym repo.
- `feedback.yml` - reakcje na opt-out i meeting.

Dashboard Phase 1 pokazuje je read-only. Edycja YAML wymaga osobnego batcha z walidacją przez modele `RuleFile`, `Rule`, `Condition` i testem decision engine.

## 8. API dashboardu

Minimalne endpointy:

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

Endpointy mutujące muszą zwracać wynik komendy i aktualny snapshot albo identyfikatory zmienionych leadów. Nie powinny udawać asynchronicznego job systemu, jeśli go jeszcze nie ma.

## 9. Frontend

Widoki Phase 1:

- Lead table z filtrami po statusie, kampanii, action i source.
- Lead detail z sekcjami T0/T0.5/T1/DecisionTrace.
- Pipeline view z licznikami i brakującymi etapami.
- Ruleset browser.
- Import CSV i akcje CLI.

UI powinno być data-dense i operacyjne. Nie projektujemy marketingowej strony ani osobnego CRM.

## 10. Auth i deploy

- Caddy + Authelia chronią host dashboardu.
- Frontend statyczny.
- Backend dostępny tylko za proxy.
- `LEADPIPE_STATE` wskazuje produkcyjny plik state.
- Backend musi mieć importowalny pakiet `leadpipe` albo dostęp do CLI w środowisku.

## 11. Future scope / Phase 2

Poniższe elementy zostają w dokumentacji jako kierunki, ale nie są wymaganiami Phase 1:

- Postgres jako aktywny storage, mimo że `leadpipe/db_schema.py` zawiera SQLAlchemy mapping.
- Alembic i migracje.
- CX webhook/importer.
- CEO inbox i role `ATTACK/SKIP`.
- Scraper ops.
- T2 Vision.
- Copywriter queue.
- Outreach/outbox.
- Pełny feedback loop i suppression UI.
- Self-Evolving Core integration.

Warunek wejścia do Phase 2: odpowiednie moduły muszą istnieć w kodzie leadpipe albo jako osobny, jawnie zaprojektowany system.
