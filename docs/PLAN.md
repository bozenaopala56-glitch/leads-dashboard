# PLAN.md — implementacja dashboardu leadpipe

## Overview

Plan jest dostosowany do aktualnego kodu `leadpipe` z `/tmp/leadpipe-t0/`. Phase 1 nie zakłada Postgresa, Alembica, CX importera, scraper ops ani CEO inbox. Dashboard ma najpierw opakować działający CLI/state pipeline:

```text
import -> scan -> decide -> pipeline
```

Każdy batch powinien używać modeli i funkcji z `leadpipe`, a nie przepisywać logiki T0/T0.5/T1/DecisionEngine.

## Batch 1: Foundation — wrapper leadpipe + frontend scaffold

### Cel

Utworzyć szkielet aplikacji: lekki backend Python, frontend React/Vite i konfigurację dostępu do `leadpipe`.

### Zadania

- Backend Python z `GET /health`.
- Settings: `LEADPIPE_STATE`, ścieżka do rulesetów, tryb wywołania `module` albo `cli`.
- Adapter `LeadpipeService`, który potrafi odczytać `.leadpipe/state.json` i zwalidować `Lead`.
- Frontend React/Vite/Tailwind z routingiem i pustym layoutem operacyjnym.
- Testy jednostkowe odczytu pustego/brakującego/zepsutego state zgodnie z zachowaniem `leadpipe.cli._load_state`.

### Akceptacja

- Backend startuje bez Postgresa.
- `GET /health` działa.
- `GET /api/state` zwraca `leads`, `scans`, `decisions`.
- Frontend build przechodzi.

## Batch 2: Lead API — state.json + komendy CLI

### Cel

Wystawić API odpowiadające funkcjom CLI.

### Zadania

- `GET /api/leads` z agregatami z `scans` i `decisions`.
- `GET /api/leads/{id}` z pełnym detail.
- `POST /api/import` obsługujący CSV zgodny z `ImportCsvSchema`.
- `POST /api/scan` dla `selector=batch` albo `lead_id`.
- `POST /api/decide` dla `selector=batch` albo `lead_id`.
- `POST /api/pipeline` dla `batchSize` i opcjonalnego pliku CSV.
- Obsługa kodów błędów CLI: import z błędami CSV zwraca błąd walidacji zamiast cichego sukcesu.

### Akceptacja

- API uruchamia realne `leadpipe import`, `scan`, `decide`, `pipeline` albo odpowiadające im funkcje.
- Po mutacji `.leadpipe/state.json` jest odświeżony.
- Nie ma własnego storage ani równoległego modelu leadów.

## Batch 3: Pipeline viz — T0/T0.5/T1 i decyzje

### Cel

Pokazać operatorowi, co faktycznie zrobił pipeline.

### Zadania

- Lead table z kolumnami: domain, company, NIP, source, status, decision action, campaign, confidence, rule key.
- Lead detail:
  - T0 signals i raw scan_result: DNS, HTTP, SSL, HTML, tech, performance.
  - T0.5 enrichment i sygnały NIP/VAT.
  - T1 JSON-LD, contact, forms, CTA, industry i sygnały.
  - Decision trace: evaluated_rules, winning_rule, blocked_by, score_breakdown, decision_reason.
- Pipeline board: counts `new`, `scanned`, `decided`, `exported`, `suppressed`, `skipped`.
- Widok braków: leady bez scan, leady scanned bez decision, decyzje bez trace.

### Akceptacja

- UI pokazuje dane obecne w `state.json`, także gdy brakuje części skanów.
- Nie pokazuje T2/copywriter/CEO jako aktywnych etapów.

## Batch 4: QA / Decision override — manual override decyzji engine

### Cel

Dodać kontrolowaną warstwę manualnego QA bez zmiany `DecisionEngine`.

### Zadania

- UI do oznaczenia decyzji jako ręcznie zweryfikowanej.
- Manual override zapisany poza natywną decyzją engine, np. w `decision.metadata.dashboard_override` albo w osobnym pliku dashboardowym powiązanym z `lead_id`.
- Dostępne override actions muszą mapować się na `DecisionAction`: `skip`, `retry`, `manual_review`, `t2_required`, `t2_optional`, `send`.
- Jeśli override ustawia `send`, kampania musi być jedną z `CampaignKey`.
- Audit: kto, kiedy, poprzednia decyzja, nowa decyzja, powód.

### Akceptacja

- Oryginalny `DecisionTrace` pozostaje widoczny.
- Operator widzi różnicę między decyzją engine i override.
- Walidacja używa enumów z `leadpipe.models`.

## Batch 5: Ruleset editor — YAML review/edit

### Cel

Pozwolić na przegląd i bezpieczną edycję rulesetów YAML.

### Zadania

- `GET /api/rulesets` i `GET /api/rulesets/{name}`.
- Edytor YAML dla:
  - `decision_gates.yml`
  - `campaigns.yml`
  - `evidence.yml`
  - `suppression.yml`
  - `t2_eligibility.yml`
  - `feedback.yml`
- Walidacja YAML przez modele `RuleFile`, `Rule`, `Condition`.
- Dry-run decision: wybrany lead + aktualny/edytowany ruleset -> preview `CampaignDecision` i `DecisionTrace`.
- Backup poprzedniej wersji przed zapisem.

### Akceptacja

- Nie da się zapisać rulesetu z nieobsługiwanym operatorem albo błędnym enumem kampanii.
- Po zapisie `DecisionEngine` ładuje rulesety bez wyjątku.
- UI oznacza `t2_eligibility` jako reguły decyzyjne, nie jako gotowy moduł T2.

## Batch 6: Deploy — build + Caddy

### Cel

Przygotować wdrożenie dashboardu bez ruszania systemów spoza leadpipe.

### Zadania

- Production build frontendu.
- Runtime backendu z ustawionym `LEADPIPE_STATE`.
- Caddy reverse proxy:
  - frontend statyczny,
  - `/api/*` do backendu,
  - Authelia forward auth.
- Healthcheck backendu.
- Instrukcja instalacji pakietu `leadpipe` albo uruchamiania z checkoutu.
- Checklist backupu `.leadpipe/state.json` przed wdrożeniem.

### Akceptacja

- `GET /health` działa za proxy.
- Frontend otwiera `/leads`, `/lead/:id`, `/pipeline`, `/rulesets`.
- `leadpipe pipeline` uruchomiony z UI aktualizuje ten sam state, który pokazuje tabela.

## Phase 2: Future Scope

Pełny plan implementacji Phase 2 jest w [FUTURE_SCOPE.md](/tmp/leads-dashboard/docs/FUTURE_SCOPE.md).

Te prace są jawnie poza realistycznym Phase 1:

- Postgres jako aktywne źródło prawdy i migracje Alembic.
- CX importer z webhooka.
- Scraper status/control.
- CEO inbox z `ATTACK/SKIP`.
- T2 Vision execution.
- Copywriter queue.
- Outreach/outbox.
- Feedback automation i suppression management UI.

Do tych tematów można wrócić po dodaniu odpowiednich modułów w leadpipe albo po decyzji, że dashboard tworzy nowy system obok leadpipe.
