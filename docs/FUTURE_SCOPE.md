# FUTURE_SCOPE.md — Phase 2 leads-dashboard

Data aktualizacji: 2026-05-27  
Zakres: kompletny plan implementacji elementów Future Scope dla `leads-dashboard` i integracji z `leadpipe` z `/tmp/leadpipe-t0/`.

## 1. Overview

### Cel Phase 2

Phase 2 zmienia dashboard z wrappera nad plikowym `state.json` w operacyjny system leadowy z trwałą bazą danych, importem z CX, kontrolą decyzji CEO, operacjami scrapera, oceną wizualną T2, generowaniem copy oraz obsługą outreachu i feedback loop.

Phase 1 ma pozostać prostym panelem nad istniejącym `leadpipe`:

```text
CSV import -> T0/T0.5/T1 scan -> DecisionEngine -> state.json -> dashboard
```

Phase 2 rozszerza ten przepływ do:

```text
CX/CSV/scraper -> Postgres -> T0/T0.5/T1 -> DecisionEngine
  -> CEO Inbox -> T2 Vision -> Copywriter -> Outreach -> Feedback/Suppression
```

Kluczowe założenie: `leadpipe` nadal jest źródłem logiki domenowej dla modeli, sygnałów, rulesetów YAML i decyzji. Dashboard Phase 2 dodaje storage, API, kolejki operacyjne i UI, ale nie przepisuje `DecisionEngine`.

### Jak Future Scope rozszerza Phase 1

- `state.json` zostaje zastąpiony Postgresem jako aktywnym źródłem prawdy.
- Obecne modele Pydantic `Lead`, `ScanResult`, `CampaignDecision`, `DecisionTrace`, `OutreachEvent`, `SuppressionEntry`, `Batch` stają się kontraktami API i mapperami do tabel.
- Istniejące `leadpipe/db_schema.py` jest punktem startowym dla SQLAlchemy async, ale wymaga Alembica, repozytoriów, migracji danych i indeksów unikalności.
- Reguły YAML pozostają źródłem decyzji automatycznych. CEO, T2 i outreach dokładają audytowalne decyzje człowieka i zdarzenia downstream.
- CSV pozostaje obsługiwany przez `ImportCsvSchema`, a feedback przez `FeedbackCsvSchema`, ale import CX i providerzy outreachu stają się dodatkowymi wejściami.

### Kolejność implementacji

1. Postgres + Alembic, bo wszystkie kolejne moduły wymagają trwałego storage i transakcji.
2. Migracja `state.json` i API kompatybilne z Phase 1, żeby nie stracić działającego pipeline.
3. CX Importer, bo dostarcza stabilny strumień leadów do bazy.
4. CEO Inbox, bo porządkuje manualne decyzje przed kosztownym T2 i wysyłką.
5. Scraper Ops, bo stabilizuje dopływ danych i diagnostykę operacyjną.
6. T2 Vision, bo wymaga istniejących leadów, decyzji i miejsca na artefakty.
7. Copywriter, bo używa sygnałów T0/T1/T2 oraz decyzji CEO.
8. Outreach, bo musi respektować suppression, decyzje CEO, wygenerowane copy i feedback.

## 2. Architektura Phase 2

```text
                         Caddy + Authelia
                               |
                         React Dashboard
                               |
                         FastAPI backend
                               |
        +----------------------+----------------------+
        |                      |                      |
  SQLAlchemy async        Service layer          Background jobs
        |                      |                      |
     Postgres          leadpipe package          scraper / T2 / copy
        |                      |                      |
        |             +--------+--------+             |
        |             |                 |             |
        |       T0/T0.5/T1         DecisionEngine     |
        |             |           YAML rulesets       |
        |             |                 |             |
        +-------------+-----------------+-------------+
                      |
      +---------------+---------------+---------------+
      |               |               |               |
   CX Bot        CEO Inbox       Vision API      Outreach API
10.186.0.10:8091 ATTACK/SKIP    screenshots     SendGrid/SMTP
```

### Integracja z istniejącym leadpipe

Backend Phase 2 powinien importować i używać:

- `leadpipe.models`: `Lead`, `LeadStatus`, `ScanResult`, `Signal`, `Evidence`, `CampaignDecision`, `DecisionTrace`, `OutreachEvent`, `SuppressionEntry`, `Batch`.
- `leadpipe.csv_schemas`: `ImportCsvSchema`, `ExportCsvSchema`, `FeedbackCsvSchema`.
- `leadpipe.engine.DecisionEngine`: ewaluacja rulesetów YAML.
- `leadpipe.t0`, `leadpipe.t0_5`, `leadpipe.t1`: skan techniczny i sygnały.
- `leadpipe.rules/*.yml`: `decision_gates`, `campaigns`, `evidence`, `suppression`, `t2_eligibility`, `feedback`.
- `leadpipe/db_schema.py`: startowy mapping SQLAlchemy, po rozbudowie o brakujące tabele Phase 2.

Nie należy w dashboardzie tworzyć alternatywnych enumów decyzji lub kampanii. UI może używać nazw biznesowych `ATTACK`, `SKIP`, `MANUAL`, ale zapis do workflow musi mapować się na istniejące `DecisionAction`: `send`, `skip`, `manual_review`, `t2_required`, `t2_optional`, `retry`.

## 3. Szczegółowy plan per moduł

## 3.1 Postgres + Alembic

### Cel

Zastąpić `.leadpipe/state.json` produkcyjnym Postgresem, dodać migracje schematu, asynchroniczny dostęp SQLAlchemy i warstwę repozytoriów. Phase 1 API ma działać dalej, ale czytać z bazy.

### Integracja z leadpipe

- Mappery `LeadRow <-> Lead`, `CampaignDecisionRow <-> CampaignDecision`, `DecisionTraceRow <-> DecisionTrace`, `ScanResultRow <-> ScanResult`.
- Import `state.json` jako jednorazowa migracja danych: `leads[]`, `scans[lead_id]`, `decisions[lead_id]`.
- `DecisionEngine.evaluate(lead, signals)` dalej przyjmuje `Lead` i słownik sygnałów z bazy.
- `leadpipe/db_schema.py` jest bazą, ale wymaga Alembica i dodatkowych tabel Phase 2.

### Nowe tabele / modele

Tabele startowe, zgodne z istniejącym `db_schema.py`:

- `batches`: `id`, `name`, `source`, `status`, `imported_count`, `accepted_count`, `rejected_count`, `metadata`, `created_at`, `updated_at`.
- `leads`: `id`, `batch_id`, `input_domain`, `normalized_domain`, `registered_domain`, `url`, `company_name`, `nip`, `source`, `contact_email`, `phone`, `status`, `metadata`, `created_at`, `updated_at`.
- `scan_results`: `id`, `lead_id`, `status`, `layer`, `started_at`, `finished_at`, `http_status`, `final_url`, `signals`, `evidence`, `raw_snapshot_path`, `error`, `metadata`, `created_at`, `updated_at`.
- `decision_traces`: `id`, `lead_id`, `ruleset_version`, `evaluated_rules`, `winning_rule`, `blocked_by`, `score_breakdown`, `decision_reason`, `created_at`.
- `campaign_decisions`: `id`, `lead_id`, `scan_result_id`, `decision_trace_id`, `action`, `campaign`, `subject`, `confidence`, `decision_reason`, `evidence_ids`, `ruleset_version`, `rule_key`, `score_breakdown`, `metadata`, `created_at`.
- `outreach_events`: `id`, `lead_id`, `campaign_decision_id`, `event`, `email`, `occurred_at`, `provider_message_id`, `notes`, `metadata`.
- `suppression_entries`: `id`, `scope`, `value`, `reason`, `active`, `permanent`, `starts_at`, `expires_at`, `source`, `metadata`.

Dodatki wymagane dla Phase 2:

- `import_events`: `id`, `source`, `source_event_id`, `idempotency_key`, `payload`, `status`, `error`, `created_at`, `processed_at`.
- `dashboard_overrides`: `id`, `lead_id`, `campaign_decision_id`, `actor`, `role`, `action`, `campaign`, `reason`, `previous_decision`, `created_at`.
- `jobs`: `id`, `type`, `status`, `lead_id`, `payload`, `attempts`, `last_error`, `locked_by`, `locked_at`, `created_at`, `updated_at`.

Wymagane indeksy:

- `uq_leads_normalized_domain_source` na `(normalized_domain, source)` z ostrożnością dla `NULL`.
- `uq_leads_nip` częściowy dla `nip IS NOT NULL`.
- `uq_import_events_idempotency_key`.
- indeksy po `leads.status`, `campaign_decisions.action`, `scan_results.layer`, `jobs.status/type`.

### Endpointy API

- `GET /health` z informacją o DB.
- `GET /api/state` jako kompatybilny snapshot dla Phase 1.
- `GET /api/leads`, `GET /api/leads/{id}`.
- `POST /api/import/state-json` do jednorazowej migracji.
- `POST /api/scan`, `POST /api/decide`, `POST /api/pipeline` działające na bazie.
- `GET /api/db/migrations`, `POST /api/db/migrations/check` tylko dla admin/ops.

### Frontend screens

- Status bazy i migracji w widoku Ops.
- Migracja `state.json`: podgląd liczby leadów, skanów, decyzji i dry-run konfliktów.
- Lead list/detail bez zmiany UX z Phase 1, ale z paginacją i filtrami serwerowymi.

### Zależności

- Stabilny Phase 1 i testy CLI.
- Dostępny Postgres na VM v3.
- Konfiguracja `DATABASE_URL`.
- Decyzja, czy migracja `state.json` jest jednorazowa, czy utrzymujemy tryb read-only fallback.

### Ryzyka

- Rozjazd między Pydantic a ORM, szczególnie `metadata` jako `meta` w SQLAlchemy.
- Utrata decyzji trace przy migracji danych z luźnego JSON.
- Race conditions, jeśli CLI nadal zapisuje `state.json`, a dashboard zapisuje DB.
- Zbyt szybkie dodanie job systemu bez retry i locking.

### Estymata

2-3 tygodnie, w tym migracje, repozytoria, testy integracyjne, migracja danych i przełączenie API Phase 1 na DB.

## 3.2 CX Importer

### Cel

Przyjmować leady od CX bota pod `10.186.0.10:8091`, importować je do leadpipe i wykonywać idempotentny upsert. Import nie może tworzyć duplikatów przy retry webhooka.

### Integracja z leadpipe

- Payload CX mapujemy do `Lead` oraz pól zgodnych z `ImportCsvSchema`: `domain`, `url`, `company_name`, `nip`, `source`, `contact_email`, `notes`.
- `source="cx"` lub dokładniejszy `source="cx_bot"`.
- Po imporcie lead może trafić do istniejącego pipeline T0/T0.5/T1 i `DecisionEngine`.
- Błędy walidacji mają używać tych samych zasad co import CSV.

### Nowe tabele / modele

- `cx_import_batches`: `id`, `remote_batch_id`, `source_host`, `status`, `received_count`, `accepted_count`, `rejected_count`, `created_at`, `processed_at`, `metadata`.
- `cx_import_records`: `id`, `batch_id`, `source_lead_id`, `idempotency_key`, `domain`, `payload`, `lead_id`, `status`, `errors`, `created_at`.
- Rozszerzenie `import_events`: `source="cx"`, `source_event_id`, `idempotency_key`, `payload`.

Idempotency key:

```text
cx:{source_lead_id}
```

Fallback, gdy brak `source_lead_id`:

```text
cx:{normalized_domain}:{contact_email|nip|company_name}
```

### Endpointy API

- `POST /api/import/cx/webhook` - przyjmuje webhook CX, wymaga tokenu lub allowlist IP.
- `GET /api/import/cx/events` - lista importów i błędów.
- `GET /api/import/cx/events/{id}` - detail payloadu i walidacji.
- `POST /api/import/cx/events/{id}/replay` - ponowne przetworzenie po naprawie mapowania.
- `GET /api/import/cx/schema` - dokumentacja oczekiwanego payloadu dla CX.

### Frontend screens

- CX Imports: strumień zdarzeń, status, liczba przyjętych/odrzuconych leadów.
- Import detail: surowy payload, wynik walidacji, powiązany `lead_id`.
- Reprocess action dla admin/ops.

### Zależności

- Postgres + unikalne indeksy.
- Uzgodniony kontrakt payloadu CX.
- Sieć między dashboardem a `10.186.0.10:8091`.
- Sekret webhooka lub mTLS/proxy allowlist.

### Ryzyka

- CX bot może wysyłać częściowe lub zmienne payloady.
- Retry webhooka bez idempotencji stworzy duplikaty.
- Brak stabilnego identyfikatora po stronie CX utrudni upsert.
- Dane osobowe i opt-out muszą być honorowane od pierwszego importu.

### Estymata

1-2 tygodnie po Postgresie, zależnie od stabilności kontraktu CX.

## 3.3 CEO Inbox

### Cel

Dodać widok leadów oczekujących na decyzję CEO i workflow `ATTACK / SKIP / MANUAL` z bulk decisions. CEO zatwierdza lub blokuje dalsze kosztowne działania: T2, copywriter, outreach.

### Integracja z leadpipe

- Kandydaci do inboxa pochodzą z `CampaignDecision.action`:
  - `manual_review`,
  - `t2_required`,
  - `t2_optional`,
  - `send` wymagające finalnej akceptacji przed outreach.
- `ATTACK` mapuje się na zgodę na dalszy etap: `send` albo `t2_required` zależnie od braków.
- `SKIP` mapuje się na `DecisionAction.SKIP` i opcjonalnie `SuppressionEntry`.
- `MANUAL` mapuje się na `DecisionAction.MANUAL_REVIEW` z przypisaniem do operatora.
- Oryginalny `DecisionTrace` pozostaje nienaruszony; decyzja CEO jest osobnym audytem.

### Nowe tabele / modele

- `ceo_inbox_items`: `id`, `lead_id`, `campaign_decision_id`, `state`, `priority`, `recommended_action`, `recommended_campaign`, `reason`, `assigned_to`, `created_at`, `updated_at`, `decided_at`.
- `ceo_decisions`: `id`, `inbox_item_id`, `lead_id`, `actor`, `decision`, `campaign`, `reason`, `bulk_operation_id`, `created_at`.
- `bulk_operations`: `id`, `type`, `actor`, `status`, `requested_count`, `succeeded_count`, `failed_count`, `payload`, `created_at`, `completed_at`.

Przykładowe stany:

- `pending`
- `approved_attack`
- `skipped`
- `manual`
- `expired`

### Endpointy API

- `GET /api/ceo/inbox?state=pending&campaign=&priority=`.
- `GET /api/ceo/inbox/{id}`.
- `POST /api/ceo/inbox/{id}/decision` z `decision=ATTACK|SKIP|MANUAL`.
- `POST /api/ceo/inbox/bulk-decision`.
- `GET /api/ceo/decisions`.
- `POST /api/ceo/inbox/rebuild` do odtworzenia inboxa z aktualnych decyzji engine.

### Frontend screens

- CEO Inbox: kolejka kart/tabeli z domeną, firmą, kampanią, confidence, reason, evidence.
- Lead review drawer: sygnały T0/T1/T2, DecisionTrace, link do strony.
- Bulk mode: zaznaczanie leadów, jedna decyzja, powód, podsumowanie skutków.
- Audit view: historia decyzji CEO.

### Zależności

- Postgres.
- Role z Authelii: `ceo`, `admin`.
- Stabilne agregaty lead detail i decision trace.

### Ryzyka

- Zbyt szeroki bulk approve może przepchnąć słabe leady do outreachu.
- `ATTACK/SKIP/MANUAL` są nazwami biznesowymi, więc trzeba jasno mapować je na `DecisionAction`.
- Brak dobrego audytu utrudni wyjaśnienie wysyłki lub blokady.

### Estymata

1.5-2.5 tygodnia.

## 3.4 Scraper Ops

### Cel

Pokazać status i umożliwić kontrolę scrapera: PID, health, logi, start/stop/restart wyłącznie dla allowlisty procesów i komend.

### Integracja z leadpipe

- Scraper dostarcza leady lub domeny do importu/pipeline, ale nie zastępuje T0/T1.
- Wyniki scrapera trafiają do `batches`, `leads`, `import_events` albo `cx_import_records`, zależnie od źródła.
- Jeśli scraper tworzy CSV, import używa `ImportCsvSchema`.

### Nowe tabele / modele

- `scraper_processes`: `id`, `name`, `command_key`, `pid`, `status`, `host`, `started_at`, `stopped_at`, `last_heartbeat_at`, `metadata`.
- `scraper_commands`: `id`, `process_id`, `actor`, `command`, `status`, `requested_at`, `completed_at`, `stdout_tail`, `stderr_tail`, `error`.
- `scraper_log_offsets`: `id`, `process_id`, `log_path`, `offset`, `updated_at`.
- Opcjonalnie `scraper_runs`: `id`, `process_id`, `status`, `started_at`, `finished_at`, `produced_count`, `imported_count`, `error`.

### Endpointy API

- `GET /api/scraper/status`.
- `GET /api/scraper/processes`.
- `GET /api/scraper/processes/{id}/logs?tail=200`.
- `POST /api/scraper/processes/{id}/start`.
- `POST /api/scraper/processes/{id}/stop`.
- `POST /api/scraper/processes/{id}/restart`.
- `GET /api/scraper/commands`.

### Frontend screens

- Scraper Ops dashboard: status, PID, uptime, heartbeat, ostatni run.
- Log viewer z tail i filtrem poziomu.
- Control panel dostępny tylko dla `ops/admin`.
- Command history z aktorem i wynikiem.

### Zależności

- Ustalony sposób uruchamiania scrapera: systemd jest preferowany.
- Allowlista `command_key -> systemctl service` zamiast dowolnego shell command.
- Dostęp backendu do logów albo journald.
- Role Authelia: `ops`, `admin`.

### Ryzyka

- Start/stop przez web UI jest ryzykowny, jeśli backend ma zbyt szerokie uprawnienia.
- Bez systemd łatwo o osierocone procesy i niepewny PID.
- Log tail może ujawnić sekrety, jeśli scraper je loguje.

### Estymata

1-2 tygodnie, jeśli scraper ma systemd service i przewidywalne logi. 2-3 tygodnie, jeśli trzeba najpierw uporządkować uruchamianie scrapera.

## 3.5 T2 Vision

### Cel

Wykonać screenshoty stron i ocenić je wizualnie pod kątem wyglądu, CTA, mobile, trust i dopasowania kampanii. Wynik T2 ma wzmacniać lub rozstrzygać decyzje `t2_required` i `t2_optional`.

### Integracja z leadpipe

- `DecisionEngine` już zna akcje `t2_required` i `t2_optional` oraz ruleset `t2_eligibility.yml`.
- Wyniki T2 zapisujemy jako `ScanResult.layer="t2"`, `SignalSource.T2`, `EvidenceType.VISUAL`.
- Sygnały T2 muszą pasować do istniejących reguł kampanii: `visual_outdated`, `not_mobile_friendly`, `mobile_layout_broken`, `tap_targets_bad`, `mobile_text_unreadable`, `weak_cta`, `low_trust`.
- Po T2 uruchamiamy ponownie `DecisionEngine.evaluate()` z sygnałami T0/T0.5/T1/T2.

### Nowe tabele / modele

- `vision_runs`: `id`, `lead_id`, `status`, `provider`, `model`, `started_at`, `finished_at`, `error`, `metadata`.
- `screenshots`: `id`, `lead_id`, `vision_run_id`, `viewport`, `url`, `storage_path`, `width`, `height`, `sha256`, `captured_at`.
- `vision_assessments`: `id`, `lead_id`, `vision_run_id`, `score_visual`, `score_cta`, `score_mobile`, `score_trust`, `summary`, `signals`, `evidence`, `raw_response`, `created_at`.

Minimalne sygnały:

- `visual_outdated: bool`
- `cta_visible: bool`
- `weak_cta: bool`
- `not_mobile_friendly: bool`
- `mobile_layout_broken: bool`
- `low_trust: bool`
- `trust_elements_present: list[str]`
- `vision_confidence: float`

### Endpointy API

- `POST /api/t2/vision/run` z `lead_id` lub listą leadów.
- `GET /api/t2/vision/runs`.
- `GET /api/t2/vision/runs/{id}`.
- `GET /api/leads/{id}/t2`.
- `POST /api/t2/vision/runs/{id}/redecide`.
- `GET /api/t2/screenshots/{id}`.

### Frontend screens

- T2 Queue: leady z `t2_required/t2_optional`.
- T2 Detail: desktop/mobile screenshot, score, sygnały, evidence, raw model summary.
- Compare view: T0/T1 vs T2 i nowa decyzja po re-evaluation.
- Manual correction: operator może oznaczyć błędny sygnał jako overridden, bez usuwania raw assessment.

### Zależności

- Postgres i storage na screenshoty.
- Headless browser, np. Playwright.
- Dostęp do modelu vision.
- CEO Inbox albo przynajmniej kolejka kwalifikacji do T2.

### Ryzyka

- Koszt API vision i screenshotów przy dużej skali.
- Modele vision mogą halucynować oceny; potrzebny jest raw screenshot i audyt.
- Strony mogą blokować headless browser.
- Mobile screenshoty są podatne na cookie banners i popups.

### Estymata

2-4 tygodnie dla wersji produkcyjnej z kolejką, storage, retry, limitami kosztów i re-decision.

## 3.6 Copywriter

### Cel

Generować personalizowane copy outreachowe na podstawie sygnałów T0/T1/T2, decyzji kampanii, evidence i decyzji CEO. Copy ma być audytowalne, wersjonowane i zatwierdzane przed wysyłką.

### Integracja z leadpipe

- Kampania pochodzi z `CampaignDecision.campaign` i enumu `CampaignKey`.
- Temat startowy może pochodzić z `CampaignDecision.subject`.
- Evidence pochodzi z `ScanResult.evidence`, `CampaignDecision.evidence_ids`, `DecisionTrace` i `vision_assessments`.
- Feedback z outreachu wraca do reguł `feedback.yml` i suppression.

### Nowe tabele / modele

- `copy_jobs`: `id`, `lead_id`, `campaign_decision_id`, `status`, `provider`, `model`, `prompt_version`, `created_at`, `updated_at`, `error`.
- `copy_variants`: `id`, `copy_job_id`, `lead_id`, `variant_index`, `subject`, `body_text`, `body_html`, `cta`, `personalization_facts`, `risk_flags`, `score`, `status`, `created_at`.
- `copy_reviews`: `id`, `copy_variant_id`, `actor`, `decision`, `reason`, `created_at`.
- `prompt_versions`: `id`, `name`, `version`, `template`, `active`, `created_at`.

Statusy:

- job: `queued`, `running`, `succeeded`, `failed`, `cancelled`.
- variant: `draft`, `approved`, `rejected`, `sent`.

### Endpointy API

- `POST /api/copy/jobs`.
- `GET /api/copy/jobs`.
- `GET /api/copy/jobs/{id}`.
- `POST /api/copy/jobs/{id}/regenerate`.
- `POST /api/copy/variants/{id}/review`.
- `PATCH /api/copy/variants/{id}` do ręcznej edycji.
- `GET /api/copy/prompt-versions`.

### Frontend screens

- Copy Queue: lead, kampania, status, reviewer.
- Copy editor: subject/body, fakty personalizacji, evidence, wersje.
- Approval workflow: approve/reject/regenerate/edit.
- Prompt versions: read-only w pierwszej iteracji, edycja tylko admin.

### Zależności

- T0/T1 działa stabilnie.
- T2 Vision dla kampanii wymagających oceny wizualnej.
- CEO `ATTACK` dla leadów, które mają wejść do copy.
- Wybrany provider LLM i polityka danych.

### Ryzyka

- Copy może zawierać niezweryfikowane twierdzenia; musi bazować na evidence.
- Brak review może prowadzić do wysyłki złego lub ryzykownego maila.
- Personalizacja po danych publicznych może wymagać ostrożnego języka.

### Estymata

2-3 tygodnie dla generowania, review, edycji i wersjonowania promptów.

## 3.7 Outreach

### Cel

Obsłużyć kampanie wysyłkowe, tracking otwarć, odpowiedzi, bounce, opt-out i feedback loop. Outreach jest ostatnim etapem i musi respektować suppression oraz decyzje CEO/copy review.

### Integracja z leadpipe

- `OutreachEvent` i `OutreachEventType` już istnieją w `leadpipe.models`.
- `FeedbackCsvSchema` istnieje jako kontrakt importu feedbacku.
- Zdarzenia `hard_bounce`, `opt_out`, `meeting`, `positive_reply` powinny aktualizować `suppression_entries` i sygnały dla `feedback.yml`.
- Wysyłka może nastąpić tylko dla leadów z zaakceptowanym copy i bez aktywnej suppression.

### Nowe tabele / modele

- `outreach_campaigns`: `id`, `name`, `campaign_key`, `status`, `provider`, `from_email`, `created_at`, `updated_at`.
- `outreach_recipients`: `id`, `campaign_id`, `lead_id`, `copy_variant_id`, `email`, `status`, `scheduled_at`, `sent_at`, `last_event_at`, `provider_message_id`.
- `outreach_messages`: `id`, `recipient_id`, `subject`, `body_text`, `body_html`, `provider_payload`, `created_at`.
- `outreach_events`: istniejąca tabela, rozszerzona operacyjnie przez relację do `recipient_id`.
- `webhook_events`: `id`, `provider`, `event_id`, `event_type`, `payload`, `processed`, `created_at`, `processed_at`.
- `suppression_entries`: używane aktywnie dla bounce, opt-out, cooldown, active customer.

### Endpointy API

- `POST /api/outreach/campaigns`.
- `GET /api/outreach/campaigns`.
- `GET /api/outreach/campaigns/{id}`.
- `POST /api/outreach/campaigns/{id}/schedule`.
- `POST /api/outreach/recipients/{id}/send-test`.
- `POST /api/outreach/recipients/{id}/cancel`.
- `POST /api/outreach/webhooks/{provider}`.
- `GET /api/outreach/events`.
- `POST /api/outreach/feedback/import-csv`.
- `GET /api/suppression`, `POST /api/suppression`, `PATCH /api/suppression/{id}`.

### Frontend screens

- Outreach Campaigns: status, wysłane, otwarcia, odpowiedzi, bounce, opt-out.
- Campaign detail: recipients, copy, timeline zdarzeń.
- Suppression UI: email/domain/NIP/phone/lead/batch, powód, expiry.
- Feedback import: CSV zgodny z `FeedbackCsvSchema`.
- Provider webhook monitor: zdarzenia nieprzetworzone i błędy.

### Zależności

- Postgres.
- CEO approval.
- Approved copy.
- Provider wysyłki i DNS domeny wysyłkowej.
- Suppression i opt-out działające przed pierwszą wysyłką.

### Ryzyka

- Deliverability wymaga konfiguracji SPF/DKIM/DMARC i reputacji domeny.
- Tracking open jest niedokładny przez blokowanie pikseli.
- Odpowiedzi i bounce zależą od jakości webhooków providera.
- Compliance i opt-out muszą być bezbłędne, bo to moduł najwyższego ryzyka.

### Estymata

3-5 tygodni dla integracji provider API, webhooków, suppression, UI kampanii i feedback loop.

## 4. Roadmapa

| Faza | Moduły | Czas | Zależności |
| --- | --- | --- | --- |
| 2.0 | Projekt techniczny DB, kontrakty API, migracja `state.json` dry-run | 3-5 dni | Phase 1 stabilny, dostęp do VM |
| 2.1 | Postgres + Alembic + repozytoria + API Phase 1 na DB | 2-3 tygodnie | Postgres, `DATABASE_URL`, testy leadpipe |
| 2.2 | CX Importer + import events + idempotentny upsert | 1-2 tygodnie | Postgres, kontrakt CX, auth webhooka |
| 2.3 | CEO Inbox + bulk decisions + audit | 1.5-2.5 tygodnia | Postgres, Authelia role, decyzje engine |
| 2.4 | Scraper Ops status/logs/control | 1-2 tygodnie | systemd/logi scrapera, role ops/admin |
| 2.5 | T2 Vision + screenshots + model assessment + re-decision | 2-4 tygodnie | Postgres, storage, Playwright, model vision |
| 2.6 | Copywriter + queue + variants + review | 2-3 tygodnie | CEO approval, T2 dla wizualnych kampanii, LLM provider |
| 2.7 | Outreach + provider webhooks + suppression + feedback loop | 3-5 tygodni | Approved copy, suppression, DNS/provider |

### Krytyczna ścieżka

```text
Postgres + Alembic
  -> migracja state/API DB
  -> CX Importer
  -> CEO Inbox
  -> T2 Vision
  -> Copywriter
  -> Outreach
```

Scraper Ops może iść równolegle po Postgresie, jeśli uruchamianie scrapera jest już uporządkowane przez systemd. Outreach nie powinien startować produkcyjnie przed suppression, opt-out i audytem decyzji CEO.

## 5. Decyzje architektoniczne

### Postgres vs SQLite

Wybór: Postgres.

Uzasadnienie:

- Potrzebne są transakcje, blokady jobów, indeksy częściowe, JSONB i równoległy dostęp API/jobów.
- `leadpipe/db_schema.py` już używa PostgreSQL `JSONB` i `UUID`.
- Phase 2 ma webhooki, background jobs, bulk decisions i outreach events; SQLite będzie wąskim gardłem operacyjnym.
- Postgres lepiej obsłuży audyt i idempotencję.

SQLite może zostać tylko jako lokalny tryb developerski, jeśli mappingi będą kompatybilne bez `JSONB`.

### Synchroniczny vs async scraper control

Wybór: API synchronicznie przyjmuje komendę, ale wykonanie kontroli jest asynchroniczne przez allowlistę/systemd.

Uzasadnienie:

- `POST /restart` powinien szybko zapisać `scraper_commands` i zwrócić status `accepted`.
- Worker lub adapter systemd wykonuje start/stop/restart i zapisuje wynik.
- UI odświeża status i historię komend.
- Backend nie powinien wykonywać dowolnych shell commands z requestu.

### T2: lokalny model vs API

Wybór startowy: API vision, np. Gemini Vision lub podobny provider, z możliwością późniejszego lokalnego modelu.

Uzasadnienie:

- Jakość i czas wdrożenia są ważniejsze niż pełna lokalność w pierwszej wersji.
- T2 jest etapem selektywnym, uruchamianym tylko dla `t2_required/t2_optional`, więc koszt da się limitować.
- Screenshot i raw response zapisujemy w audycie, żeby móc porównywać providerów.

Lokalny model ma sens później, jeśli koszt API lub polityka danych staną się problemem.

### Outreach: własny SMTP vs API

Wybór startowy: provider API, np. SendGrid, Mailgun, Resend lub podobny, zamiast własnego SMTP.

Uzasadnienie:

- Provider daje webhooki bounce/reply/open, event IDs, retry i lepsze narzędzia deliverability.
- Własny SMTP zwiększa ryzyko reputacji, observability i obsługi bounce.
- Outreach wymaga feedback loop, a provider API znacząco skraca wdrożenie.

Własny SMTP można rozważyć dopiero po stabilizacji wolumenu, reputacji domeny i wymagań compliance.

## 6. Checklist gotowości

- [ ] leadpipe Phase 1 stabilny (testy przechodzą)
- [ ] VM v3 z Postgres
- [ ] CX bot działa i ma endpoint `/api/leads`
- [ ] Scraper działa i pisze logi
- [ ] Authelia działa i ma grupy (`admin`, `ceo`, `ops`)
- [ ] Caddy reverse proxy skonfigurowany
- [ ] Ustalony `DATABASE_URL` i backup Postgresa
- [ ] Ustalona polityka migracji z `state.json`
- [ ] Ustalony sekret webhooka CX lub allowlista IP
- [ ] Ustalony storage screenshotów T2
- [ ] Ustalony provider vision i limity kosztów
- [ ] Ustalony provider outreach, domena wysyłkowa, SPF/DKIM/DMARC
- [ ] Ustalona polityka opt-out i suppression przed wysyłką
