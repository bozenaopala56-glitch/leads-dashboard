# TDD_PLAN.md — plan Test-Driven Development dla dashboardu leadpipe

Data: 2026-05-27  
Zakres: Phase 1 dashboardu jako lekki wrapper nad `/tmp/leadpipe-t0/`, `.leadpipe/state.json`, CLI/funkcjami `leadpipe` oraz obecnym frontendem vanilla JS.

## 1. Filozofia TDD

Każdy task zaczyna się od testu, który najpierw nie przechodzi.

- **RED** — napisz test opisujący oczekiwany kontrakt API, modelu, stanu albo UI. Test ma pęknąć z powodu braku implementacji, a nie przez błąd w fixture.
- **GREEN** — napisz minimalny kod produkcyjny, który spełnia test. Nie duplikuj logiki `leadpipe`; importuj modele, CLI albo funkcje pipeline.
- **REFACTOR** — uporządkuj kod bez zmiany zachowania. Po refaktorze uruchom ten sam zestaw testów.

Zasady obowiązkowe:

- Testy powstają przed kodem produkcyjnym.
- Dashboard nie tworzy własnej logiki T0/T0.5/T1 ani własnego `DecisionEngine`.
- Źródłem prawdy Phase 1 jest `LEADPIPE_STATE` wskazujący `.leadpipe/state.json`.
- Modele domenowe pochodzą z `leadpipe.models`; DTO dashboardu są dopuszczalne tylko jako modele widokowe.
- Frontend Phase 1 pozostaje vanilla JS zgodny z obecnym `leadpipe/dashboard/`.
- Endpointy batchowe z tego planu są warstwą dashboardową nad kontraktem CLI: `import`, `scan`, `decide`, `pipeline`.

## 2. Struktura testów

```text
dashboard/
  tests/
    conftest.py              # fixtures wspólne
    test_backend.py          # testy API backendu
    test_models.py           # testy modeli Pydantic/serializacji
    test_state.py            # testy odczytu/zapisu state.json
    test_integration.py      # testy end-to-end backend + leadpipe
    test_frontend_smoke.py   # smoke frontend, opcjonalnie Playwright/Selenium
```

Preferowane narzędzia:

- `pytest`
- `fastapi.testclient.TestClient` albo klient testowy Flask, zależnie od wybranego backendu
- `tmp_path` i `monkeypatch.setenv("LEADPIPE_STATE", ...)`
- `unittest.mock`/`pytest.monkeypatch` dla komend CLI i wolnych modułów sieciowych
- Playwright tylko dla smoke UI; jeśli nie zostanie dodany, testy frontendowe oznaczyć `@pytest.mark.optional`

## 3. Fixtures i mocki bazowe

### `dashboard/tests/conftest.py`

Planowane fixtures:

- `state_path(tmp_path, monkeypatch)` — ustawia `LEADPIPE_STATE` na tymczasowy plik.
- `empty_state()` — zwraca `{"leads": [], "scans": {}, "decisions": {}}`.
- `sample_lead()` — instancja `leadpipe.models.Lead` z domeną, firmą, NIP, emailem i statusem `new`.
- `sample_lead_json(sample_lead)` — `sample_lead.model_dump(mode="json")`.
- `sample_scan_payload(sample_lead)` — `scans[lead_id]` z sekcjami `t0`, `t0_5`, `t1`.
- `sample_decision_payload(sample_lead)` — `decisions[lead_id]` z `CampaignDecision` i `DecisionTrace`.
- `state_with_one_lead(...)` — kompletny snapshot z jednym leadem, skanem i decyzją.
- `write_state(state_path, payload)` — zapisuje JSON do pliku.
- `api_client(state_path)` — klient testowy aplikacji.
- `auth_headers()` — nagłówki symulujące Authelię, np. `Remote-User`, `Remote-Email`, `Remote-Groups`.
- `csv_file(tmp_path)` — poprawny CSV zgodny z `ImportCsvSchema`.
- `invalid_csv_file(tmp_path)` — CSV z brakującą domeną albo błędnym emailem.

Mocki wspólne:

- `leadpipe.cli.command_import`, `command_scan`, `command_decide`, `command_pipeline` — w testach API mutujących.
- `leadpipe.cli._load_state`, `_save_state` — w testach izolujących backend od dysku.
- `leadpipe.t0.run_t0_batch`, `leadpipe.t0_5.run_t0_5`, `leadpipe.t1.run_t1` — w integracjach bez sieci.
- `DecisionEngine.evaluate` — tylko tam, gdzie test dotyczy endpointu, a nie samego engine.
- `pathlib.Path.read_text/write_text/replace` albo warstwa `StateStore` — w testach błędów IO i atomic write.

## 4. Plan testów per task z `docs/PLAN.md`

### Batch 1 / T1 — Backend Python z `GET /health` i `GET /api/health`

Plik: `dashboard/tests/test_backend.py`

Funkcje testowe:

- `test_health_returns_ok_without_postgres`
  - Given backend uruchomiony z tymczasowym `LEADPIPE_STATE`, when klient wywołuje `GET /api/health`, then status to `200`, `status == "ok"` i odpowiedź nie wymaga `DATABASE_URL`.
- `test_health_reports_state_path`
  - Given ustawione `LEADPIPE_STATE`, when wywołuję `GET /api/health`, then JSON zawiera ścieżkę state albo flagę `state_configured`.
- `test_legacy_health_alias_returns_ok`
  - Given reverse proxy może sprawdzać `/health`, when klient wywołuje `GET /health`, then status to `200` i kontrakt jest zgodny z `/api/health`.
- `test_health_handles_state_read_error_as_degraded`
  - Given `StateStore.healthcheck` rzuca `OSError`, when klient wywołuje health, then odpowiedź to `200` z `status == "degraded"` albo `500` zgodnie z decyzją implementacyjną zapisaną w teście.

Fixture: `api_client`, `state_path`.  
Mocki: `StateStore.healthcheck` dla błędu IO.  
Assertion: kod HTTP, pola `status`, brak zależności od Postgresa.

### Batch 1 / T2 — Settings: `LEADPIPE_STATE`, rulesety, tryb `module` albo `cli`

Plik: `dashboard/tests/test_backend.py`

Funkcje testowe:

- `test_settings_loads_leadpipe_state_from_env`
  - Given env `LEADPIPE_STATE=/tmp/x/state.json`, when powstaje konfiguracja, then `settings.leadpipe_state` wskazuje tę ścieżkę.
- `test_settings_defaults_to_dot_leadpipe_state`
  - Given brak env, when powstaje konfiguracja, then ścieżka domyślna to `.leadpipe/state.json`.
- `test_settings_rejects_unknown_invocation_mode`
  - Given env z trybem `bad`, when waliduję settings, then dostaję błąd walidacji.
- `test_settings_accepts_module_and_cli_modes`
  - Given tryby `module` i `cli`, when waliduję settings, then oba są akceptowane.

Fixture: `monkeypatch`, `tmp_path`.  
Mocki: brak.  
Assertion: wartości konfiguracji, błąd walidacji.

### Batch 1 / T3 — Adapter `LeadpipeService` czyta state i waliduje `Lead`

Plik: `dashboard/tests/test_state.py`

Funkcje testowe:

- `test_service_loads_empty_state_when_file_missing`
  - Given plik state nie istnieje, when `LeadpipeService.load_state()`, then zwraca `leads=[]`, `scans={}`, `decisions={}` jak `leadpipe.cli._load_state`.
- `test_service_loads_valid_leads_as_pydantic_models`
  - Given state z poprawnym leadem, when serwis ładuje leady, then waliduje je przez `Lead.model_validate` i zachowuje `normalized_domain`.
- `test_service_ignores_or_reports_invalid_lead_records`
  - Given state z rekordem leadu z nieznanym polem, when serwis buduje listę, then rekord jest raportowany jako problem danych albo pominięty zgodnie z przyjętym kontraktem.
- `test_service_preserves_raw_scans_and_decisions`
  - Given state z `scans` i `decisions`, when serwis zwraca snapshot, then surowe sekcje T0/T0.5/T1 i trace są dostępne bez przepisywania.

Fixture: `state_path`, `write_state`, `sample_lead_json`, `sample_scan_payload`, `sample_decision_payload`.  
Mocki: brak albo `_load_state` dla izolacji.  
Assertion: kształt state, walidacja Pydantic, brak utraty surowych payloadów.

### Batch 1 / T4 — Frontend vanilla JS: routing/pusty layout operacyjny

Plik: `dashboard/tests/test_frontend_smoke.py`

Funkcje testowe:

- `test_index_html_loads_static_assets`
  - Given serwer statyczny dashboardu, when pobieram `/`, then status to `200` i HTML zawiera `app.js` oraz `style.css`.
- `test_frontend_has_operational_views`
  - Given `index.html`, when parsuję DOM, then istnieją sekcje lead list/detail albo batch/pipeline/rulesets zgodne z Phase 1.
- `test_app_js_fetches_api_not_sample_batch_after_batch_2`
  - Given docelowa implementacja po podłączeniu API, when analizuję `app.js`, then inicjalny fetch używa `/api/...`, a nie wyłącznie `data/sample-batch.json`.
- `test_frontend_does_not_render_phase_2_active_modules`
  - Given HTML/JS, when sprawdzam widoki, then nie ma aktywnych ekranów CEO, scraper, copywriter, outreach jako Phase 1 workflow.

Fixture: statyczny serwer albo odczyt plików.  
Mocki: odpowiedzi API w Playwright przez route mocking.  
Assertion: HTTP 200, brak błędów JS, obecność kontenerów UI.

### Batch 1 / T5 — Unit testy state: pusty/brakujący/uszkodzony state

Plik: `dashboard/tests/test_state.py`

Funkcje testowe:

- `test_load_state_missing_file_returns_empty_state`
  - Given brak pliku, when `load_state`, then zwraca pusty state.
- `test_load_state_invalid_json_returns_empty_state`
  - Given plik zawiera `{broken`, when `load_state`, then zwraca pusty state.
- `test_load_state_invalid_shape_returns_empty_state`
  - Given plik zawiera listę zamiast dict, when `load_state`, then zwraca pusty state.
- `test_load_state_partial_shape_normalizes_sections`
  - Given `{"leads": "bad", "scans": [], "decisions": null}`, when `load_state`, then typy są znormalizowane do `[]`, `{}`, `{}`.

Fixture: `state_path`, `write_state`.  
Mocki: brak.  
Assertion: zgodność z `leadpipe.cli._load_state`.

### Batch 2 / T6 — `GET /api/leads` z agregatami

Plik: `dashboard/tests/test_backend.py`

Funkcje testowe:

- `test_get_leads_returns_rows_with_scan_and_decision_aggregates`
  - Given state z leadem, skanem i decyzją, when `GET /api/leads`, then odpowiedź zawiera `id`, `normalized_domain`, `status`, `t0_confidence`, `t1_confidence`, `decision.action`, `campaign`, `rule_key`.
- `test_get_leads_handles_empty_state`
  - Given pusty state, when `GET /api/leads`, then status `200` i lista pusta.
- `test_get_leads_filters_by_status_campaign_action_source`
  - Given wiele leadów, when podaję query filtra, then API zwraca tylko pasujące rekordy.
- `test_get_leads_does_not_mutate_state`
  - Given state zapisany na dysku, when wykonuję `GET /api/leads`, then zawartość pliku nie zmienia się.

Fixture: state z wieloma leadami.  
Mocki: brak.  
Assertion: liczba rekordów, pola agregatu, brak zapisu.

### Batch 2 / T7 — `GET /api/leads/{id}` z pełnym detail

Plik: `dashboard/tests/test_backend.py`

Funkcje testowe:

- `test_get_lead_detail_returns_lead_scans_decision_trace`
  - Given state z kompletem T0/T0.5/T1 i decyzją, when `GET /api/leads/{id}`, then JSON zawiera `lead`, `scans.t0`, `scans.t0_5`, `scans.t1`, `decision`, `trace`.
- `test_get_lead_detail_returns_404_for_missing_lead`
  - Given state bez ID, when `GET /api/leads/missing`, then status `404`.
- `test_get_lead_detail_allows_missing_scan_sections`
  - Given lead bez `scans`, when pobieram detail, then status `200`, a brakujące sekcje są `null` albo `{}` zgodnie z kontraktem.
- `test_get_lead_detail_rejects_invalid_uuid_if_uuid_required`
  - Given endpoint wymaga UUID, when ID ma zły format, then status `422`; jeśli ID jest stringiem CLI, test oczekuje `404`.

Fixture: `state_with_one_lead`.  
Mocki: brak.  
Assertion: kompletność detail, kody błędów.

### Batch 2 / T8 — `POST /api/import` i `POST /api/batches`

Plik: `dashboard/tests/test_backend.py`

Funkcje testowe:

- `test_post_import_accepts_valid_csv_and_refreshes_state`
  - Given poprawny CSV, when `POST /api/import` albo `POST /api/batches`, then backend wywołuje `command_import`, zwraca `200/201` i odświeżony snapshot.
- `test_post_import_returns_422_for_invalid_csv`
  - Given CSV z błędnym emailem lub pustą domeną, when import, then status `422` i lista błędów walidacji.
- `test_post_import_returns_500_when_cli_crashes`
  - Given `command_import` rzuca wyjątek, when import, then status `500` i czytelny błąd bez częściowego sukcesu.
- `test_post_import_uses_import_csv_schema_fields`
  - Given CSV z `domain,url,company_name,nip,source,contact_email,notes`, when import, then przekazane dane są zgodne z `ImportCsvSchema`.

Fixture: `csv_file`, `invalid_csv_file`, `state_path`.  
Mocki: `leadpipe.cli.command_import` lub `parse_csv` i `command_import`.  
Assertion: kod HTTP, wywołanie CLI, snapshot po mutacji.

### Batch 2 / T9 — `POST /api/scan` i `POST /api/batches/{id}/scan`

Plik: `dashboard/tests/test_backend.py`

Funkcje testowe:

- `test_post_scan_batch_invokes_leadpipe_scan_batch`
  - Given state z leadami, when `POST /api/scan {"selector":"batch"}` albo `/api/batches/{id}/scan`, then wywołuje `command_scan` z selektorem batch.
- `test_post_scan_lead_invokes_leadpipe_scan_for_lead_id`
  - Given istniejący lead, when scan dla lead ID, then CLI/funkcja dostaje ten ID.
- `test_post_scan_returns_404_for_missing_lead_or_batch`
  - Given brak zasobu, when scan, then status `404`.
- `test_post_scan_returns_422_for_missing_selector`
  - Given pusty body, when `POST /api/scan`, then status `422`.
- `test_post_scan_returns_500_on_pipeline_error`
  - Given `run_t0_batch` albo `command_scan` rzuca wyjątek, when scan, then status `500`.

Fixture: state z leadami i batch metadata w `Lead.batch_id` albo `metadata`.  
Mocki: `command_scan`, opcjonalnie `run_t0_batch`, `run_t0_5`, `run_t1`.  
Assertion: wywołanie właściwego selektora, statusy, odświeżony state.

### Batch 2 / T10 — `POST /api/decide` i decyzje engine

Plik: `dashboard/tests/test_backend.py`

Funkcje testowe:

- `test_post_decide_batch_invokes_leadpipe_decide`
  - Given scanned leads, when `POST /api/decide {"selector":"batch"}`, then wywołuje `command_decide` i zwraca decyzje.
- `test_post_decide_lead_uses_signals_from_t0_t05_t1`
  - Given state ze skanami, when decyduję lead, then sygnały przekazane do `DecisionEngine` są scalone z `t0`, `t0_5`, `t1`.
- `test_post_decide_returns_404_when_cli_reports_missing_lead`
  - Given `command_decide` zwraca kod `1`, when endpoint, then status `404`.
- `test_post_decide_returns_422_for_invalid_selector`
  - Given selector pusty albo złego typu, when endpoint, then status `422`.

Fixture: state ze skanami.  
Mocki: `command_decide` albo `DecisionEngine.evaluate`.  
Assertion: decyzja zapisana w `decisions[lead_id]`, status leadu `decided`.

### Batch 2 / T11 — `POST /api/pipeline`

Plik: `dashboard/tests/test_backend.py`

Funkcje testowe:

- `test_post_pipeline_with_batch_size_runs_import_scan_decide`
  - Given body `{"batchSize": 10}`, when endpoint, then wywołuje `command_pipeline` i zwraca `pipeline_done`.
- `test_post_pipeline_with_file_passes_csv_path`
  - Given body z `file`, when endpoint, then CLI dostaje `--file` lub namespace z plikiem.
- `test_post_pipeline_rejects_non_positive_batch_size`
  - Given `batchSize=0`, when endpoint, then status `422`.
- `test_post_pipeline_returns_422_for_invalid_csv_errors`
  - Given CLI zwraca kod `2`, when endpoint, then status `422`, nie `200`.
- `test_post_pipeline_refreshes_state_after_mutation`
  - Given state zmienia się po pipeline, when endpoint kończy się sukcesem, then odpowiedź zawiera aktualny snapshot.

Fixture: `csv_file`, `state_path`.  
Mocki: `command_pipeline`.  
Assertion: argumenty CLI, kody błędów, snapshot.

### Batch 3 / T12 — Lead table: kolumny i filtry

Pliki: `dashboard/tests/test_backend.py`, `dashboard/tests/test_frontend_smoke.py`

Funkcje testowe:

- `test_lead_rows_include_required_columns`
  - Given state z decyzją, when `GET /api/leads`, then każdy row zawiera domain, company, NIP, source, status, decision action, campaign, confidence, rule key.
- `test_lead_rows_include_none_for_missing_decision`
  - Given lead bez decyzji, when lista, then pola decyzji są `null`, nie powodują 500.
- `test_frontend_renders_lead_table_from_api`
  - Given mock API zwraca dwa leady, when strona się ładuje, then tabela/lista pokazuje oba rekordy.
- `test_frontend_filters_reduce_visible_rows`
  - Given trzy leady w DOM, when ustawiam filtr statusu/kampanii, then liczba widocznych wierszy maleje zgodnie z filtrem.

Fixture: state z leadami w różnych statusach.  
Mocki: API w Playwright albo `fetch`.  
Assertion: pola DTO, DOM z wierszami, wynik filtrów.

### Batch 3 / T13 — Lead detail: T0/T0.5/T1 i DecisionTrace

Pliki: `dashboard/tests/test_backend.py`, `dashboard/tests/test_frontend_smoke.py`

Funkcje testowe:

- `test_detail_exposes_t0_raw_scan_result`
  - Given scan T0 zawiera DNS/HTTP/SSL/HTML/tech/performance, when detail, then wszystkie sekcje są w JSON.
- `test_detail_exposes_t05_enrichment_and_signals`
  - Given `t0_5.enrichment` i sygnały NIP/VAT, when detail, then są dostępne w odpowiedzi.
- `test_detail_exposes_t1_sections_and_signals`
  - Given `t1.jsonld`, `contacts`, `forms`, `ctas`, `industry`, when detail, then każda sekcja jest obecna.
- `test_detail_exposes_decision_trace_fields`
  - Given decyzja z trace, when detail, then `evaluated_rules`, `winning_rule`, `blocked_by`, `score_breakdown`, `decision_reason` są obecne.

Fixture: `sample_scan_payload`, `sample_decision_payload`.  
Mocki: brak.  
Assertion: kompletność payloadu detail.

### Batch 3 / T14 — Pipeline board i widok braków

Plik: `dashboard/tests/test_backend.py`

Funkcje testowe:

- `test_pipeline_counts_all_lead_statuses`
  - Given leady `new`, `scanned`, `decided`, `exported`, `suppressed`, `skipped`, when `GET /api/batches` albo endpoint boardu, then liczniki są poprawne.
- `test_pipeline_reports_leads_without_scan`
  - Given lead `new` bez `scans`, when pobieram board, then ID jest w `missing_scans`.
- `test_pipeline_reports_scanned_without_decision`
  - Given lead `scanned` ze scanem i bez decyzji, when board, then ID jest w `missing_decisions`.
- `test_pipeline_reports_decisions_without_trace`
  - Given `decisions[lead_id].decision` bez `trace`, when board, then ID jest w `decisions_missing_trace`.

Fixture: state z mieszanymi statusami.  
Mocki: brak.  
Assertion: liczniki, listy braków, brak aktywnych etapów Phase 2.

### Batch 4 / T15 — Manual override decyzji engine

Plik: `dashboard/tests/test_backend.py`

Funkcje testowe:

- `test_override_stores_dashboard_override_without_replacing_trace`
  - Given lead z decyzją engine, when operator zapisuje override, then oryginalny `DecisionTrace` pozostaje bez zmian.
- `test_override_accepts_only_decision_action_enum_values`
  - Given action spoza `DecisionAction`, when override, then status `422`.
- `test_override_send_requires_campaign_key`
  - Given action `send` bez kampanii, when override, then status `422`.
- `test_override_audit_contains_actor_previous_new_and_reason`
  - Given nagłówki Authelii i poprzednia decyzja, when override, then audit zawiera aktora, czas, poprzednią decyzję, nową decyzję i powód.
- `test_override_visible_next_to_engine_decision`
  - Given zapisany override, when `GET /api/leads/{id}`, then response pokazuje osobno `engine_decision` i `dashboard_override`.

Fixture: state z decyzją, `auth_headers`.  
Mocki: zegar (`utcnow`) dla stabilnej daty.  
Assertion: walidacja enumów, audit, trace bez zmian.

### Batch 5 / T16 — Ruleset browser/editor YAML

Plik: `dashboard/tests/test_backend.py`

Funkcje testowe:

- `test_get_rulesets_lists_allowed_yaml_files`
  - Given katalog rulesetów, when `GET /api/rulesets`, then zwraca tylko `decision_gates.yml`, `campaigns.yml`, `evidence.yml`, `suppression.yml`, `t2_eligibility.yml`, `feedback.yml`.
- `test_get_ruleset_returns_content_and_version`
  - Given istniejący ruleset, when `GET /api/rulesets/campaigns.yml`, then status `200`, treść YAML i `version`.
- `test_get_ruleset_rejects_path_traversal`
  - Given nazwa `../secrets`, when endpoint, then status `404` albo `400`.
- `test_save_ruleset_rejects_invalid_yaml`
  - Given błędny YAML, when zapis, then status `422`.
- `test_save_ruleset_validates_rulefile_rule_condition`
  - Given YAML z nieobsługiwanym operatorem albo błędnym `CampaignKey`, when zapis, then status `422`.
- `test_save_ruleset_creates_backup_before_replace`
  - Given poprawny YAML, when zapis, then stary plik ma backup przed nadpisaniem.
- `test_dry_run_decision_returns_decision_and_trace`
  - Given lead i edytowany ruleset, when dry-run, then API zwraca `CampaignDecision` i `DecisionTrace` bez zapisu do state.

Fixture: tymczasowy katalog rulesetów.  
Mocki: `DecisionEngine(rules_dir=...)`, filesystem backup.  
Assertion: walidacja YAML, brak path traversal, dry-run bez mutacji.

### Batch 6 / T17 — Deploy: build, runtime, Caddy/Authelia

Pliki: `dashboard/tests/test_backend.py`, `dashboard/tests/test_frontend_smoke.py`, testy skryptów deploy jeśli powstaną.

Funkcje testowe:

- `test_backend_uses_runtime_leadpipe_state_env`
  - Given env produkcyjny z `LEADPIPE_STATE`, when backend startuje w teście, then API czyta ten plik.
- `test_api_health_works_behind_forwarded_headers`
  - Given nagłówki proxy, when `GET /api/health`, then status `200`.
- `test_authelia_missing_headers_returns_401_when_auth_enabled`
  - Given `AUTH_ENABLED=true` i brak nagłówków Authelii, when request do `/api/leads`, then status `401`.
- `test_authelia_group_without_permission_returns_403`
  - Given użytkownik bez grupy `ops/admin`, when mutujący endpoint, then status `403`.
- `test_static_frontend_routes_are_served_for_spa_paths`
  - Given statyczny frontend, when `GET /leads`, `/lead/{id}`, `/pipeline`, `/rulesets`, then zwraca HTML aplikacji.

Fixture: `auth_headers`, env auth.  
Mocki: brak lub middleware auth.  
Assertion: runtime env, auth, ścieżki statyczne.

## 5. Testy backend API per endpoint Phase 1

Poniższa lista używa endpointów z zadania. Jeśli implementacja zachowa aliasy z dokumentacji (`/api/import`, `/api/scan`, `/api/decide`, `/api/pipeline`), każdy test powinien mieć wariant aliasu albo osobny test kompatybilności.

### `GET /api/health`

- `test_api_health_200`
  - Given aplikacja działa, when `GET /api/health`, then `200` i `status=ok`.
- `test_api_health_422_not_applicable`
  - Given endpoint bez parametrów, when wywołuję z nieznanym query, then ignoruje query albo zwraca `422` zgodnie z kontraktem.
- `test_api_health_500_on_unhandled_healthcheck_error`
  - Given healthcheck rzuca nieobsłużony wyjątek, when request, then `500`.
- `test_api_health_auth_bypass_or_401_when_enabled`
  - Given Authelia włączona, when brak nagłówków, then health jest jawnie publiczny `200` albo chroniony `401`; decyzję utrwalić testem.

### `GET /api/batches`

- `test_get_batches_200_with_counts`
  - Given state z leadami w batchach, when request, then `200` i liczniki.
- `test_get_batches_422_for_invalid_query`
  - Given `limit=bad`, when request, then `422`.
- `test_get_batches_404_for_unknown_active_batch_filter`
  - Given query `activeBatchId=missing`, when request, then `404`.
- `test_get_batches_500_on_state_error`
  - Given odczyt state rzuca, when request, then `500`.
- `test_get_batches_401_or_403_when_auth_enabled`
  - Given auth włączone i brak/brak uprawnień, when request, then `401/403`.

### `GET /api/batches/{id}/leads`

- `test_get_batch_leads_200`
  - Given batch z dwoma leadami, when request, then `200` i dwa rekordy.
- `test_get_batch_leads_422_for_invalid_pagination`
  - Given `offset=-1`, when request, then `422`.
- `test_get_batch_leads_404_for_missing_batch`
  - Given brak batcha, when request, then `404`.
- `test_get_batch_leads_500_on_state_error`
  - Given błąd state, when request, then `500`.
- `test_get_batch_leads_401_403_when_auth_enabled`
  - Given auth, when brak nagłówków albo grupy, then `401/403`.

### `GET /api/leads/{id}`

- `test_get_lead_200`
  - Given istniejący lead, when request, then `200` i detail.
- `test_get_lead_422_for_invalid_id_if_uuid_contract`
  - Given niepoprawny UUID, when request, then `422`; dla string ID oczekiwać `404`.
- `test_get_lead_404_for_missing_id`
  - Given brak leada, when request, then `404`.
- `test_get_lead_500_on_state_error`
  - Given błąd odczytu, when request, then `500`.
- `test_get_lead_401_403_when_auth_enabled`
  - Given auth, when brak albo zła grupa, then `401/403`.

### `POST /api/batches` — import CSV

- `test_post_batches_200_or_201_valid_csv`
  - Given poprawny CSV, when upload, then `200/201`.
- `test_post_batches_422_missing_file_or_invalid_csv`
  - Given brak pliku albo błędny CSV, when request, then `422`.
- `test_post_batches_404_not_applicable_for_create`
  - Given create nie zależy od zasobu, when endpoint działa, then nie zwraca `404`; jeśli podany `sourceBatchId` nie istnieje, then `404`.
- `test_post_batches_500_on_cli_error`
  - Given CLI rzuca, when request, then `500`.
- `test_post_batches_401_403_when_auth_enabled`
  - Given auth, when brak albo zła grupa, then `401/403`.

### `POST /api/batches/{id}/scan`

- `test_post_batch_scan_200`
  - Given istniejący batch, when scan, then `200` i wynik skanu.
- `test_post_batch_scan_422_for_invalid_body`
  - Given body z błędną opcją, when request, then `422`.
- `test_post_batch_scan_404_for_missing_batch`
  - Given brak batcha, when request, then `404`.
- `test_post_batch_scan_500_on_pipeline_error`
  - Given pipeline rzuca, when request, then `500`.
- `test_post_batch_scan_401_403_when_auth_enabled`
  - Given auth, when brak albo zła grupa, then `401/403`.

### `GET /api/decisions`

- `test_get_decisions_200`
  - Given state z decyzjami, when request, then `200` i lista decyzji z trace.
- `test_get_decisions_422_for_invalid_filter`
  - Given `confidenceMin=bad`, when request, then `422`.
- `test_get_decisions_404_for_missing_batch_filter`
  - Given filtr batcha nie istnieje, when request, then `404`.
- `test_get_decisions_500_on_state_error`
  - Given błąd state, when request, then `500`.
- `test_get_decisions_401_403_when_auth_enabled`
  - Given auth, when brak albo zła grupa, then `401/403`.

### `POST /api/export`

- `test_post_export_200_csv`
  - Given decyzje `send` i brak suppression, when export CSV, then `200`, `text/csv`, nagłówki i rekordy.
- `test_post_export_422_missing_format_or_invalid_filter`
  - Given brak wymaganego formatu albo błędny batch ID, when request, then `422`.
- `test_post_export_404_for_missing_batch`
  - Given batch nie istnieje, when export, then `404`.
- `test_post_export_500_on_state_or_csv_error`
  - Given `dump_csv` rzuca, when request, then `500`.
- `test_post_export_401_403_when_auth_enabled`
  - Given auth, when brak albo zła grupa, then `401/403`.

## 6. Testy modeli i serializacji

Plik: `dashboard/tests/test_models.py`

Modele z `leadpipe.models`, które muszą mieć test serializacji użyty przez dashboard:

- `Lead`
- `Signal`
- `Evidence`
- `ScanResult`
- `CampaignDecision`
- `DecisionTrace`
- `RuleEvaluation`
- `ScoreBreakdown`
- `Batch`
- enumy `LeadStatus`, `DecisionAction`, `CampaignKey`
- CSV: `ImportCsvSchema`, `FeedbackCsvSchema`, `ExportCsvSchema`

Funkcje testowe:

- `test_lead_serializes_to_api_json`
  - Given `Lead` z domeną, NIP i emailem, when `model_dump(mode="json")`, then JSON ma string UUID/datetime i status `new`.
- `test_campaign_decision_serializes_and_send_requires_campaign`
  - Given decyzja `send`, when brak kampanii, then walidacja pęka; when kampania jest poprawna, then JSON zawiera `campaign`.
- `test_decision_trace_serializes_nested_rules_and_score`
  - Given trace z `RuleEvaluation` i `ScoreBreakdown`, when dump/validate, then pola nested zachowują typy.
- `test_scan_result_serializes_signals_and_evidence`
  - Given `ScanResult` z `Signal` i `Evidence`, when serializacja, then nested modele są poprawne.
- `test_missing_optional_fields_use_none_or_defaults`
  - Given minimalne modele, when walidacja, then opcjonalne pola mają `None`, listy/dicty są puste.
- `test_strict_models_reject_unknown_fields`
  - Given dodatkowe pole w modelu leadpipe, when walidacja, then `ValidationError`.
- `test_api_lead_row_dto_does_not_mutate_lead_contract`
  - Given DTO widokowe, when buduję row, then pola agregatu są poza `Lead`, nie dopisane do modelu `Lead`.

## 7. Testy `state.json`

Plik: `dashboard/tests/test_state.py`

Funkcje testowe:

- `test_state_reads_existing_file`
  - Given poprawny state na dysku, when backend czyta, then zwraca `leads`, `scans`, `decisions`.
- `test_state_missing_file_returns_empty`
  - Given brak pliku, when czytam, then pusty state.
- `test_state_invalid_json_returns_empty_or_data_error`
  - Given uszkodzony JSON, when czytam, then zgodnie z kontraktem `leadpipe.cli._load_state` pusty state.
- `test_state_invalid_section_types_are_normalized`
  - Given złe typy sekcji, when czytam, then `leads=[]`, `scans={}`, `decisions={}`.
- `test_state_save_is_atomic`
  - Given zapis state, when `_save_state` albo wrapper zapisuje, then używa pliku `.tmp` i `replace`.
- `test_state_write_creates_parent_directory`
  - Given katalog nie istnieje, when zapisuję, then katalog i plik powstają.
- `test_state_concurrent_reads_during_write_do_not_return_partial_json`
  - Given równoczesny zapis i odczyt, when czytam wielokrotnie, then nigdy nie dostaję częściowego JSON.
- `test_state_permission_error_returns_500_in_api`
  - Given `read_text` rzuca `OSError`, when API czyta state, then endpoint zwraca `500` albo zdegradowany health zgodnie z kontraktem.

## 8. Testy integracyjne

Plik: `dashboard/tests/test_integration.py`

### Import CSV → leadpipe import → state.json → API → frontend

- `test_integration_import_csv_to_api_leads`
  - Given pusty `LEADPIPE_STATE` i poprawny CSV, when `POST /api/batches`, then state ma leady, a `GET /api/batches/{id}/leads` pokazuje import.
- `test_integration_import_invalid_csv_returns_validation_errors`
  - Given CSV z błędami, when import, then state pozostaje pusty i API zwraca `422`.
- `test_integration_frontend_fetches_imported_leads`
  - Given API po imporcie, when frontend ładuje dane, then tabela renderuje importowane leady.

Mocki: w tym scenariuszu nie mockować `parse_csv`; można mockować tylko wolne operacje sieciowe, których import nie używa.

### Scan batcha → leadpipe scan → sygnały T0/T0.5/T1 → API

- `test_integration_scan_batch_writes_t0_t05_t1`
  - Given state z leadem, when `POST /api/batches/{id}/scan`, then `scans[lead_id]` ma `t0`, `t0_5`, `t1`.
- `test_integration_scan_batch_updates_lead_status_scanned`
  - Given lead `new`, when scan, then `Lead.status == scanned`.
- `test_integration_scan_handles_partial_t0_failure`
  - Given mock `run_t0_batch` zwraca `scan_failed_final`, when scan, then API nie gubi błędu i zapisuje go w `scans`.

Mocki: `run_t0_batch`, `run_t0_5`, `run_t1`, żeby test był deterministyczny i bez sieci.

### DecisionEngine → decyzja → API → UI

- `test_integration_decide_writes_decision_and_trace`
  - Given lead ze skanami i sygnałami, when `POST /api/decide`, then `decisions[lead_id].decision` i `trace` są zapisane.
- `test_integration_decision_detail_matches_engine_output`
  - Given realny `DecisionEngine` i sygnały trust campaign, when detail, then `campaign == REDESIGN_TRUST`, `winning_rule == CAMPAIGN_REDESIGN_TRUST`.
- `test_integration_frontend_shows_engine_decision`
  - Given API zwraca decyzję, when frontend renderuje detail, then użytkownik widzi action, campaign, rule key i confidence.

Mocki: nie mockować `DecisionEngine` w teście kampanii; mockować tylko T0/T0.5/T1.

## 9. Testy frontend smoke

Plik: `dashboard/tests/test_frontend_smoke.py`

Funkcje testowe:

- `test_frontend_page_loads_200`
  - Given uruchomiony backend/statyczny serwer, when `GET /`, then status `200`.
- `test_frontend_console_has_no_errors`
  - Given Playwright i mock API, when strona się ładuje, then `console.error` jest puste.
- `test_frontend_table_renders_api_data`
  - Given `/api/batches/{id}/leads` zwraca dwa rekordy, when frontend się ładuje, then DOM pokazuje dwie pozycje.
- `test_frontend_filters_reduce_rows`
  - Given trzy rekordy, when wpisuję filtr domeny/statusu, then liczba widocznych wierszy spada.
- `test_frontend_export_button_calls_api_export`
  - Given widok eksportu, when klikam export, then frontend wykonuje `POST /api/export`.
- `test_frontend_handles_empty_state`
  - Given API zwraca pusty state, when strona się ładuje, then UI pokazuje pustą tabelę bez błędów JS.

Jeśli Playwright nie zostanie dodany w Phase 1, minimalny smoke można wykonać bez przeglądarki:

- pobrać `/`, `/app.js`, `/style.css`;
- statycznie sprawdzić, że `app.js` używa `/api/`;
- testy DOM oznaczyć jako oczekujące na zależność Playwright.

## 10. Kolejność implementacji TDD

### Batch A — infrastruktura testów

Cel: testy startowe, które nie zależą od pełnej domeny.

1. `dashboard/tests/conftest.py`
2. `test_health_returns_ok_without_postgres`
3. `test_api_health_200`
4. `test_index_html_loads_static_assets`

Oczekiwany RED: brak aplikacji testowej albo brak endpointu.  
GREEN: minimalny backend i serwowanie statycznych plików.

### Batch B — modele i state

Cel: zablokować kontrakty danych przed API.

1. `test_lead_serializes_to_api_json`
2. `test_campaign_decision_serializes_and_send_requires_campaign`
3. `test_decision_trace_serializes_nested_rules_and_score`
4. `test_state_missing_file_returns_empty`
5. `test_state_invalid_json_returns_empty_or_data_error`
6. `test_service_loads_valid_leads_as_pydantic_models`

Oczekiwany RED: brak `StateStore`/`LeadpipeService`.  
GREEN: minimalny adapter nad `leadpipe.cli._load_state`.

### Batch C — API odczytowe

Cel: najpierw bez mutacji.

1. `GET /api/state`
2. `GET /api/batches`
3. `GET /api/batches/{id}/leads`
4. `GET /api/leads/{id}`
5. `GET /api/decisions`

Oczekiwany RED: endpointy nie istnieją.  
GREEN: DTO budowane z `state.json`, bez zapisu.

### Batch D — API mutujące nad CLI

Cel: import, scan, decide, pipeline z mockowanym CLI.

1. `POST /api/batches`
2. `POST /api/import`
3. `POST /api/batches/{id}/scan`
4. `POST /api/scan`
5. `POST /api/decide`
6. `POST /api/pipeline`
7. `POST /api/export`

Oczekiwany RED: brak endpointów lub brak mapowania kodów CLI.  
GREEN: minimalne wywołanie `leadpipe.cli` i odświeżenie state.

### Batch E — pipeline visualization i frontend smoke

Cel: UI pokazuje dane z API.

1. lead table z wymaganymi kolumnami;
2. lead detail z T0/T0.5/T1/DecisionTrace;
3. pipeline board i widok braków;
4. smoke JS bez błędów konsoli;
5. filtry frontendowe.

Oczekiwany RED: frontend nadal czyta `sample-batch.json`.  
GREEN: `fetch("/api/...")` i render pustych/brakujących danych.

### Batch F — override, rulesety, deploy/auth

Cel: funkcje wyższego ryzyka po stabilnym core.

1. manual override z audytem;
2. ruleset browser i walidacja YAML;
3. dry-run decision;
4. Authelia 401/403;
5. smoke za proxy i runtime `LEADPIPE_STATE`.

Oczekiwany RED: brak endpointów/middleware.  
GREEN: minimalny zapis override poza oryginalnym trace, read-only rulesety przed edycją.

## 11. Kryteria gotowości planu

- [x] Każdy task z Phase 1 w `docs/PLAN.md` ma przypisane testy.
- [x] Każdy endpoint API z zadania ma minimum 4 przypadki testowe.
- [x] Każdy aktywny model leadpipe używany przez dashboard ma test serializacji.
- [x] Są testy edge cases: puste dane, błędy, brak pliku, invalid JSON, brak zasobu, błędy CLI.
- [x] Fixtures i mocki są zdefiniowane.
- [x] Plan jest podzielony na niezależne batche możliwe do wykonania w kolejnych uruchomieniach Codex CLI.
